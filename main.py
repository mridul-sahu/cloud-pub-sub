import collections
import json
import logging
import os
import urllib

import cloudstorage
import jinja2
import webapp2
from google.appengine.api import images
from google.appengine.ext import blobstore
from google.appengine.ext import ndb
import googleapiclient.discovery

THUMBNAIL_BUCKET = 'open-dev-test-thumb'
PHOTO_BUCKET = 'open-dev-test'
NUM_NOTIFICATIONS_TO_DISPLAY = 5
MAX_LABELS = 10

#Path to templates
template_dir = os.path.join(os.path.dirname(__file__), 'templates')

#jinja template enviroment to load templates from
jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(template_dir))


def create_notification(photo_name,
                    event_type,
                    generation,
                    overwrote_generation=None,
                    overwritten_by_generation=None):
    if event_type == 'OBJECT_FINALIZE':
        # We overwrote an older version of the image.
        if overwrote_generation is not None:
            message = '{} was uploaded and overwrote an older' \
                ' version of itself.'.format(photo_name)
        else:
            message = '{} was uploaded.'.format(photo_name)

    elif event_type == 'OBJECT_ARCHIVE':
        # We were trying to archive an older version of the image.
        if overwritten_by_generation is not None:
            message = '{} was overwritten by a newer version.'.format(
                photo_name)
        else:
            message = '{} was archived.'.format(photo_name)

    elif event_type == 'OBJECT_DELETE':
        if overwritten_by_generation is not None:
            # We were trying to delete an older version of the image.
            message = '{} was overwritten by a newer version.'.format(
                photo_name)
        else:
            message = '{} was deleted.'.format(photo_name)

    # Note: If the event_type is OBJECT_METADATA_UPDATE, the message field is None,
    # i.e we don't send notifications when only metadata of image changes.
    else:
        message = None

    return Notification(message=message, generation=generation)

def create_thumbnail(photo_name):
    filename = '/gs/{}/{}'.format(PHOTO_BUCKET, photo_name)
    image = images.Image(filename=filename)
    image.resize(width=180, height=200)
    # The service accepts image data in the JPEG, PNG, WEBP, GIF (including animated GIF), BMP, TIFF and ICO formats.
    # Transformed images can be returned in the JPEG, WEBP and PNG formats.
    # If the input format and the output format are different,
    # the service converts the input data to the output format before performing the transformation.
    return image.execute_transforms(output_encoding=images.JPEG)

def store_thumbnail_in_gcs(thumbnail_key, thumbnail):
    write_retry_params = cloudstorage.RetryParams(
        backoff_factor=1.1,
        max_retry_period=15)
    filename = '/{}/{}'.format(THUMBNAIL_BUCKET, thumbnail_key)
    with cloudstorage.open(
            filename, 'w', content_type='image/jpeg',
            retry_params=write_retry_params) as filehandle:
        filehandle.write(thumbnail)

def get_labels(uri, photo_name):
    service = googleapiclient.discovery.build('vision', 'v1')
    labels = set()

    # Label photo with its name, sans extension.
    photo_details = os.path.splitext(photo_name) # cute-dog.jpg => ["cute-dog",".jpg"]
    labels.add(photo_details[0])

    service_request = service.images().annotate(body={
        'requests': [{
            'image': {
                'source': {
                    'imageUri': uri
                }
            },
            'features': [{
                'type': 'LABEL_DETECTION',
                'maxResults': MAX_LABELS
            }]
        }]
    })
    response = service_request.execute()
    labels_full = response['responses'][0].get('labelAnnotations')

    ignore = set(['of', 'like', 'the', 'and', 'a', 'an', 'with'])

    # Add labels to the labels list if they are not already in the list
    # and are not in the ignore list.
    if labels_full is not None:
        for label in labels_full:
            if label['description'] not in labels:
                labels.add(label['description'])
                # Split the label into individual words, also to be added to
                # labels list if not already.
                descriptors = label['description'].split()
                for descript in descriptors:
                    if descript not in labels and descript not in ignore:
                        labels.add(descript)

    return labels

def get_original_url(photo_name, generation):
    original_photo = 'https://storage.googleapis.com/' \
        '{}/{}?generation={}'.format(
            PHOTO_BUCKET,
            photo_name,
            generation)
    return original_photo

def get_thumbnail_serving_url(photo_name):
    filename = '/gs/{}/{}'.format(THUMBNAIL_BUCKET, photo_name)
    blob_key = blobstore.create_gs_key(filename)
    return images.get_serving_url(blob_key)

def delete_thumbnail(thumbnail_key):
    filename = '/gs/{}/{}'.format(THUMBNAIL_BUCKET, thumbnail_key)

    blob_key = blobstore.create_gs_key(filename)
    images.delete_serving_url(blob_key)

    thumbnail_reference = ThumbnailReference.query(
        ThumbnailReference.thumbnail_key == thumbnail_key).get()
    thumbnail_reference.key.delete()

    storage_filename = '/{}/{}'.format(THUMBNAIL_BUCKET, thumbnail_key)
    cloudstorage.delete(storage_filename)

# Google Datastore NDB Client Library allows App Engine Python apps to connect to Cloud Datastore
class Notification(ndb.Model):
    message = ndb.StringProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)
    generation = ndb.StringProperty()

class ThumbnailReference(ndb.Model):
    thumbnail_name = ndb.StringProperty()
    thumbnail_key = ndb.StringProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)
    labels = ndb.StringProperty(repeated=True)
    original_photo = ndb.StringProperty()

class MainHandler(webapp2.RequestHandler):
    def get(self):

        # Fetch notification from Cloud Datastore
        notifications = Notification.query().order(
        -Notification.date).fetch(NUM_NOTIFICATIONS_TO_DISPLAY)

        template_values = {'notifications': notifications}

        template = jinja_environment.get_template('home.html')
        self.response.write(template.render(template_values))

class PhotosHandler(webapp2.RequestHandler):
    def get(self):

        thumbnail_references = ThumbnailReference.query().order(
        -ThumbnailReference.date).fetch()
        thumbnails = collections.OrderedDict()

        for thumbnail_reference in thumbnail_references:
            img_url = get_thumbnail_serving_url(thumbnail_reference.thumbnail_key)
            thumbnails[img_url] = thumbnail_reference

        template_values = {'thumbnails': thumbnails}

        template = jinja_environment.get_template('photos.html')
        self.response.write(template.render(template_values))

class SearchHandler(webapp2.RequestHandler):
    def get(self):
        template_values = {} #Nothing yet to pass to the template
        template = jinja_environment.get_template('search.html')
        self.response.write(template.render(template_values))

class ReceiveMessage(webapp2.RequestHandler):
    def post(self):
        logging.debug('Post body: {}'.format(self.request.body))

        message = json.loads(urllib.unquote(self.request.body))
        attributes = message['message']['attributes']

        #Acknowledge Reception
        self.response.status = 204

        #Extracting the relevant info
        event_type = attributes.get('eventType')
        photo_name = attributes.get('objectId')
        generation_number = str(attributes.get('objectGeneration'))
        overwrote_generation = attributes.get('overwroteGeneration')
        overwritten_by_generation = attributes.get('overwrittenByGeneration')

        # try:
        #     index = photo_name.index('.jpg')
        # except:
        #     return
        # thumbnail_key = '{}{}{}'.format(photo_name[:index], generation_number, photo_name[index:])

        #I would want to support more than just '.jpg' files
        photo_details = os.path.splitext(photo_name) # cute-dog.jpg => ["cute-dog",".jpg"]
        thumbnail_key = '{}{}{}'.format(photo_details[0], generation_number, photo_details[1])

        new_notification = create_notification(
                                photo_name,
                                event_type,
                                generation_number,
                                overwrote_generation=overwrote_generation,
                                overwritten_by_generation=overwritten_by_generation)

        if new_notification.message is None:
            return

        # Cloud Pub/Sub messaging guarantees at-least-once delivery,
        # meaning a Cloud Pub/Sub notification may be received more than once.
        # If the notification already exists,
        # there has been no new change to the Cloud Storage photo bucket,
        # and the Cloud Pub/Sub notification can be ignored.

        exists_notification = Notification.query(
        Notification.message == new_notification.message,
        Notification.generation == new_notification.generation).get()

        if exists_notification:
            return

        # Put notification in Cloud Datastore
        new_notification.put()

        if event_type == 'OBJECT_FINALIZE':
            thumbnail = create_thumbnail(photo_name)
            store_thumbnail_in_gcs(thumbnail_key, thumbnail)

            uri = 'gs://{}/{}'.format(PHOTO_BUCKET, photo_name)
            labels = get_labels(uri, photo_name)
            original_photo = get_original_url(photo_name, generation_number)

            thumbnail_reference = ThumbnailReference(
                                    thumbnail_name=photo_name,
                                    thumbnail_key=thumbnail_key,
                                    labels=list(labels),
                                    original_photo=original_photo)
            thumbnail_reference.put()

        elif event_type == 'OBJECT_DELETE' or event_type == 'OBJECT_ARCHIVE':
            delete_thumbnail(thumbnail_key)

app = webapp2.WSGIApplication([
        ('/', MainHandler),
        ('/photos', PhotosHandler),
        ('/search', SearchHandler),
        ('/_ah/push-handlers/receive_message', ReceiveMessage)], debug=True)
