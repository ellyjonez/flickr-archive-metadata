# Flickr Archiver with Metadata

# What

This is a simple python tool that creates a complete local backup of your Flickr photos, including and metadata like comments, who faved, and location info. It also saves this same metadata for your favorited photos. 

# Why

Flickr gives users a way to download all their photos, but those downloads don't include associated data you might also want to preserve such as sweet comments left by people who've long since died, who faved it, photo locations, original upload date, tags, etc. 

In January 2025, Flickr enforced a new rule that free users could no longer have more than 50 private photos. In this enforcement action, Flickr catastrophically deleted my late mom's private photos, including her detailed captions and comments, with almost no notification that this would happen. They claim they sent multiple warnings to affected account holders via email, but there was no evidence of this in the email associated with my mom's account. I realized even if I had downloaded her photos via Flickr's basic downloader, I would not have the captions or comments.

I am hoping this saves someone else from losing cherished photos, captions, comments, though for lots of people it's too late. 

## Features

- **Photo Backup**: Downloads the original resolution photo
- **Saves all the Metadata that is shown on Flickr pages**: 
  - Photo titles, descriptions, and captions
  - Uploaded and taken dates
  - Geolocation coordinates
  - View counts and stats
  - Tags
  - Album/Set memberships
- **Social Data**: 
  - Comments with commenter info and avatars
  - Favorites with user details
- **EXIF Data**: Camera settings and technical metadata
- **Favorites Backup**: Also archives photos you've favorited from other users
- **Resume Support**: Skip already downloaded content on subsequent runs
- **User Info Caching**: Efficiently fetches user details for commenters and fans

## Data Structure

Running this will create an organized json formatted archive on your local computer:

```
flickr_archive/
├── my_photos/
│   ├── [photo_id]/
│   │   ├── original.jpg          # Original resolution photo
│   │   ├── metadata.json         # Title, description, dates, tags, location
│   │   ├── comments.json         # Comments with user info
│   │   ├── favorites.json        # Users who favorited with details
│   │   ├── exif.json            # Camera/technical data
│   │   ├── sizes.json           # Available sizes info
│   │   └── complete.flag        # Indicates successful download
├── favorited_photos/            # Photos you've favorited (same structure)
├── my_photos_index.json         # Searchable index of your photos
├── favorites_index.json         # Index of favorited photos
├── albums_index.json            # List of all your albums/sets
└── users_cache.json             # Cached user info for efficiency
```

## Requirements

- Python 3.7+
- Flickr API key and secret
- macOS/Linux/Windows with command line access, or some place you can run some python scripts

## Setup

1. **Clone the repository**
   ```bash
   git clone git@github.com:ellyjonez/flickr-archive-metadata.git
   cd flickr-archive-metadata
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install the flickr api dependency**
   ```bash
   pip install flickrapi requests
   ```

4. **Configure API credentials**
   - Copy `config_sample.py` to `config.py`
   - Add your Flickr API credentials:
   ```python
   API_KEY = 'your_api_key_here'
   API_SECRET = 'your_api_secret_here'  
   USER_ID = 'your_user_id@N00'
   ```
   
   To get an API key, you need to register a third party app with Flickr. Unfortunately, you will need a paid Flickr pro account to do this. Feel free to email me if you would like to use my Flickr app info to run this archiver.
   - API Key & Secret: https://www.flickr.com/services/apps/create/

   - User ID: This is not your human readable username, it's numeric - it looks something like '413469512@N05' If you never created a custom username it might be in your profile URL. Otherwise, you can fetch it using https://www.webfx.com/tools/idgettr/ 

## Usage

1. **Run the downloader**
   ```bash
   python downloader.py
   ```

2. **First run authentication**
   - The first time you run it, the script will prompt you to authorize - it will open a browser for Flickr authorization
   - Grant read access to your account
   - Enter the verification code shown by Flickr

3. **Monitor progress**
   - The script shows progress like `[148/3220]` for each photo
   - Already downloaded photos are skipped automatically

## Doesn't save videos! You must save them manually

If you have a lot of videos this might be a problem. 
Flickr's API doesn't provide direct video downloads. For videos:

- The tool saves the metadata with a poster frame as `poster.jpg`
- Video metadata includes Flickr page URLs
- Manually download videos from Flickr using the saved URLs

To find all videos:
```bash
find flickr_archive -name "metadata.json" -exec grep -l '"media": "video"' {} \;
```

## How do I browse my archive?

You can't yet, it's just a bunch of JSON. My goal is to eventually build a front-end that can consume this JSON so that you can locally 'browse' your Flickr photos and captions with archival records of comments. I can't backup all of Flickr - I wish I could, as it was a monumental cultural record, but at least this way people can create personal archives if their photos are still there.

## Resuming Downloads

If you have a lot of pics, downloading could take some time, because there is a sleep built in to avoid rate limiting. 

The downloader is designed to be stopped and resumed:
- Each photo folder gets a `complete.flag` file when fully downloaded
- Subsequent runs skip photos with this flag
- Interrupt safely with Ctrl+C anytime

## Sample Output format 

- metadata.json has the photo info
- sizes.json has the sizes w/ URLs (does not download every size)
- comments.json 
- favorites.json
- 

```json
{
  "id": "12345678901",
  "title": "Sunset at the Beach",
  "description": "Beautiful sunset captured at Malibu",
  "date_uploaded": "1609459200",
  "date_uploaded_formatted": "2021-01-01T00:00:00",
  "date_taken": "2021-01-01 18:30:00",
  "tags": ["sunset", "beach", "malibu"],
  "views": 42,
  "location": {
    "latitude": 34.0259,
    "longitude": -118.7798,
    "locality": {"_content": "Malibu"},
    "country": {"_content": "United States"}
  },
  "albums": [{
    "id": "72157677634567890",
    "title": "California Sunsets"
  }]
}
```

## Useful Commands

**Find photos with comments:**
```bash
find flickr_archive -name "comments.json" -exec grep -l '"text":' {} \;
```

**Count total archived items:**
```bash
find flickr_archive -name "metadata.json" | wc -l
```

**Remove complete flags to re-download:**
```bash
find flickr_archive -name "complete.flag" -delete
```
