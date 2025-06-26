# flickr_client.py
import flickrapi
import time
from config import API_KEY, API_SECRET

# Initialize with authentication support
flickr = flickrapi.FlickrAPI(API_KEY, API_SECRET, format='parsed-json')

def retry_on_error(func):
    """Decorator to retry API calls on temporary failures"""
    def wrapper(*args, **kwargs):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except flickrapi.exceptions.FlickrError as e:
                if '201' in str(e) or 'not currently available' in str(e):
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 5  # 5, 10, 15 seconds
                        print(f"  API temporarily unavailable, waiting {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                raise
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"  Error: {e}, retrying...")
                    time.sleep(2)
                    continue
                raise
        return None
    return wrapper

# Check if we need to authenticate
if not flickr.token_valid(perms='read'):
    print("This application needs to authenticate to access your private photos.")
    print("Opening browser for authorization...")
    
    # Get a request token
    flickr.get_request_token(oauth_callback='oob')
    
    # Open a browser at the authentication URL
    authorize_url = flickr.auth_url(perms='read')
    print(f"\nPlease visit this URL to authorize the application:")
    print(authorize_url)
    
    # Get the verifier code from the user
    verifier = input('\nEnter the verification code from Flickr: ').strip()
    
    # Trade the request token for an access token
    flickr.get_access_token(verifier)
    print("Authentication successful!")

def get_photos(user_id, per_page=500, page=1):
    """Get ALL photos for a user (public and private)"""
    return flickr.people.getPhotos(
        user_id=user_id, 
        per_page=per_page, 
        page=page,
        extras='date_upload,date_taken,geo,tags,machine_tags,o_dims,views,media'
    )

def get_photo_info(photo_id):
    """Get detailed info about a photo"""
    return flickr.photos.getInfo(photo_id=photo_id)

def get_photo_comments(photo_id):
    """Get all comments for a photo"""
    try:
        return flickr.photos.comments.getList(photo_id=photo_id)
    except:
        return {'comments': {'comment': []}}

def get_photo_favorites(photo_id):
    """Get list of users who favorited this photo"""
    try:
        return flickr.photos.getFavorites(photo_id=photo_id, per_page=500)
    except:
        return {'photo': {'person': []}}

def get_photo_exif(photo_id):
    """Get EXIF data for a photo"""
    try:
        return flickr.photos.getExif(photo_id=photo_id)
    except:
        return {'photo': {'exif': []}}

def get_photo_sizes(photo_id):
    """Get all available sizes for a photo"""
    return flickr.photos.getSizes(photo_id=photo_id)

def get_photo_geo(photo_id):
    """Get geolocation data for a photo"""
    try:
        return flickr.photos.geo.getLocation(photo_id=photo_id)
    except:
        return None

def get_favorites(user_id, per_page=500, page=1):
    """Get photos favorited by the user"""
    return flickr.favorites.getList(
        user_id=user_id,
        per_page=per_page,
        page=page,
        extras='date_upload,date_taken,geo,tags,owner_name'
    )

def get_photo_stats(photo_id, date=None):
    """Get stats for a photo (requires authentication)"""
    try:
        return flickr.stats.getPhotoStats(photo_id=photo_id)
    except:
        return None

def get_photo_contexts(photo_id):
    """Get all contexts (sets/pools) for a photo"""
    try:
        return flickr.photos.getAllContexts(photo_id=photo_id)
    except:
        return {'set': []}

def get_photosets(user_id):
    """Get all photosets (albums) for a user"""
    return flickr.photosets.getList(user_id=user_id, per_page=500)

def get_user_info(user_id):
    """Get user info including buddy icon"""
    try:
        return flickr.people.getInfo(user_id=user_id)
    except:
        return None