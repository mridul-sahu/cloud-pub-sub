# cloud-pub-sub

## Description
Implementation of the tutorial "How to Use Cloud Pub/Sub Notifications and Cloud Storage with App Engine".

You can find the tutorial at **[How to Use Cloud Pub/Sub Notifications and Cloud Storage with App Engine
](https://cloud.google.com/community/tutorials/use-cloud-pubsub-cloud-storage-app-engine)**

This tutorial teaches you how to integrate several Google products to simulate a shared photo album, hosted on App Engine standard environment and managed through the Cloud Platform Console. The web application has three pages.

Users interact with the web application only through the Cloud Platform Console; photos cannot be uploaded or deleted through the website. Behind the scenes, two buckets exist in **Cloud Storage**: one to store the uploaded photos and the other to store the thumbnails of the uploaded photos. **Cloud Datastore** stores all non-image entities needed for the web application, which is hosted on **App Engine**. Notifications of changes to the **Cloud Storage** photo bucket are sent to the application by using **Cloud Pub/Sub**. The **Google APIs Client Library for the Cloud Vision API** is used to label photos for search.

## Overview

### Receiving a notification

1. A user uploads or deletes something from their Cloud Storage photo bucket.
2. A Cloud Pub/Sub message is sent.
3. The Cloud Pub/Sub message is received by App Engine.
4. The Cloud Pub/Sub message is formatted and stored as a `Notification` in Cloud Datastore.
5. If the event type from the message is `OBJECT_FINALIZE`, the uploaded photo is compressed and stored as a thumbnail in a separate Cloud Storage thumbnail bucket. If the event type from the message is `OBJECT_DELETE` or `OBJECT_ARCHIVE`, the thumbnail matching the name and generation number of the deleted or archived photo is deleted from the Cloud Storage thumbnail bucket. When an object is removed from your Cloud Storage photo bucket, the event type will be OBJECT_DELETE if **versioning** is not turned on for your bucket and `OBJECT_ARCHIVE` if versioning is turned on for your bucket.
6. If the event type from the message is `OBJECT_FINALIZE`, then the Google Cloud Vision API is used to generate labels for the uploaded photo.
7. If the event type from the message is `OBJECT_FINALIZE`, then a new `ThumbnailReference` is created and stored in Cloud Datastore. If the event type from the message is `OBJECT_DELETE` or `OBJECT_ARCHIVE`, then the appropriate `ThumbnailReference` is deleted from Cloud Datastore.

### Loading the home page

1. The user navigates to `[YOUR_PROJECT_ID].appspot.com`.
2. A predetermined number of `Notifications` are queried from Cloud Datastore, ordered by date and time, most recent first.
3. The queried `Notifications` are sent to the front-end to be formatted and displayed on the home page.
4. The HTML file links to an external CSS file for styling.

### Loading the photos page
1. The user navigates to `[YOUR_PROJECT_ID].appspot.com/photos`.
2. All the `ThumbnailReferences` are fetched from Cloud Datastore, ordered by date and time, most recent first.
3. Each `ThumbnailReference` is used to get a serving url for the corresponding thumbnail stored in the Cloud Storage thumbnail bucket.
4. A dictionary of `ThumbnailReferences` and their serving urls is sent to the front-end to be formatted and displayed on the photos page.
5. The HTML file links to an external CSS file for styling.

### Loading the search page

1. The user navigates to `[YOUR_PROJECT_ID].appspot.com/search`. The user enters a search term.
2. All the `ThumbnailReferences` are fetched from Cloud Datastore, ordered by date and time, most recent first.
3. Each queried `ThumbnailReference` that contains the search term as one of its `labels` is used to get a serving url for the corresponding thumbnail stored in the Cloud Storage thumbnail bucket.
4. A dictionary of `ThumbnailReferences` that contain the search term as one of their `labels` and their serving urls is sent to the front-end to be formatted and displayed on the search page.
5. The HTML file links to an external CSS file for styling.

## Setup

**Follow the tutorial's [Setup Section](https://cloud.google.com/community/tutorials/use-cloud-pubsub-cloud-storage-app-engine#set-up)**
