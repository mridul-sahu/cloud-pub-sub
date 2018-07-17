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
      template_values = {} #Nothing yet to pass to the template
      template = jinja_environment.get_template('home.html')
      self.response.write(template.render(template_values))

class PhotosHandler(webapp2.RequestHandler):
    def get(self):
      template_values = {} #Nothing yet to pass to the template
      template = jinja_environment.get_template('photos.html')
      self.response.write(template.render(template_values))

class SearchHandler(webapp2.RequestHandler):
    def get(self):
      template_values = {} #Nothing yet to pass to the template
      template = jinja_environment.get_template('search.html')
      self.response.write(template.render(template_values))

#TODO: Implement Recieve
class ReceiveMessage(webapp2.RequestHandler):
    def post(self):
        print 'Did you foget something?'

app = webapp2.WSGIApplication([
        ('/', MainHandler),
        ('/photos', PhotosHandler),
        ('/search', SearchHandler),
        ('/_ah/push-handlers/receive_message', ReceiveMessage)], debug=True)
