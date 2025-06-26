# downloader.py
import os
import json
import requests
import time
from datetime import datetime
from flickr_client import (
    get_photos, get_photo_info, get_photo_comments, 
    get_photo_favorites, get_photo_exif, get_photo_sizes,
    get_photo_geo, get_favorites, get_photo_stats,
    get_photo_contexts, get_photosets, get_user_info
)
from config import USER_ID

DATA_DIR = 'flickr_archive'
PHOTOS_DIR = os.path.join(DATA_DIR, 'my_photos')
FAVORITES_DIR = os.path.join(DATA_DIR, 'favorited_photos')
RATE_DELAY = 1.2 

# Cache for user info to avoid duplicate API calls
USER_CACHE = {}

def get_cached_user_info(user_id):
    """Get user info with caching to minimize API calls"""
    if user_id not in USER_CACHE:
        user_info = get_user_info(user_id)
        if user_info and 'person' in user_info:
            person = user_info['person']
            
            # Construct avatar URL
            iconserver = person.get('iconserver', '0')
            iconfarm = person.get('iconfarm', '1')
            nsid = person.get('nsid', '')
            
            if iconserver and int(iconserver) > 0:
                avatar_url = f"https://farm{iconfarm}.staticflickr.com/{iconserver}/buddyicons/{nsid}.jpg"
            else:
                avatar_url = "https://www.flickr.com/images/buddyicon.gif"
            
            # Get display name (realname if available, otherwise username)
            realname = person.get('realname', {}).get('_content', '')
            username = person.get('username', {}).get('_content', '')
            display_name = realname if realname else username
            
            USER_CACHE[user_id] = {
                'display_name': display_name,
                'username': username,
                'realname': realname,
                'avatar_url': avatar_url,
                'is_pro': person.get('ispro', 0),
                'profile_url': person.get('profileurl', {}).get('_content', '')
            }
        else:
            # Fallback for users we can't fetch
            USER_CACHE[user_id] = {
                'display_name': user_id,
                'username': user_id,
                'realname': '',
                'avatar_url': "https://www.flickr.com/images/buddyicon.gif",
                'is_pro': 0,
                'profile_url': f"https://www.flickr.com/people/{user_id}/"
            }
    
    return USER_CACHE[user_id]

def save_json(data, path):
    """Save data as JSON with proper encoding"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def download_photo(url, path):
    """Download a photo from URL to path"""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"  Error downloading photo: {e}")
        return False

def process_photo(photo, base_dir, is_favorite=False):
    """Process a single photo - fetch all metadata and download"""
    photo_id = photo['id']
    time.sleep(RATE_DELAY) 
    photo_dir = os.path.join(base_dir, photo_id)
    
    # Skip if already processed
    if os.path.exists(os.path.join(photo_dir, 'complete.flag')):
        print(f"  Skipping {photo_id} - already processed")
        return
    
    print(f"  Processing photo {photo_id}...")
    
    # Get all photo data
    info = get_photo_info(photo_id)
    
    # Create combined metadata
    metadata = {
        'id': photo_id,
        'title': info['photo'].get('title', {}).get('_content', ''),
        'description': info['photo'].get('description', {}).get('_content', ''),
        'date_uploaded': info['photo'].get('dateuploaded', ''),
        'date_uploaded_formatted': datetime.fromtimestamp(
            int(info['photo'].get('dateuploaded', 0))
        ).isoformat() if info['photo'].get('dateuploaded') else None,
        'date_taken': info['photo'].get('dates', {}).get('taken', ''),
        'tags': [tag['raw'] for tag in info['photo'].get('tags', {}).get('tag', [])],
        'views': int(info['photo'].get('views', 0)),
        'owner': info['photo'].get('owner', {}),
        'urls': info['photo'].get('urls', {}).get('url', []),
        'location': None,
        'media': info['photo'].get('media', 'photo'),
        'stats': {
            'views': int(info['photo'].get('views', 0)),
            'comments': int(info['photo'].get('comments', {}).get('_content', 0)),
            'favorites': int(info['photo'].get('isfavorite', 0))
        }
    }
    
    # Add owner info for favorites
    if is_favorite:
        metadata['owner_name'] = photo.get('ownername', '')
    
    # Get geolocation
    geo_data = get_photo_geo(photo_id)
    if geo_data and 'photo' in geo_data:
        metadata['location'] = {
            'latitude': geo_data['photo']['location'].get('latitude'),
            'longitude': geo_data['photo']['location'].get('longitude'),
            'accuracy': geo_data['photo']['location'].get('accuracy'),
            'locality': geo_data['photo']['location'].get('locality', {}),
            'county': geo_data['photo']['location'].get('county', {}),
            'region': geo_data['photo']['location'].get('region', {}),
            'country': geo_data['photo']['location'].get('country', {})
        }
    
    # Get album/photoset information
    contexts = get_photo_contexts(photo_id)
    albums = []
    if 'set' in contexts:
        for photoset in contexts['set']:
            albums.append({
                'id': photoset.get('id'),
                'title': photoset.get('title'),
                'primary': photoset.get('primary'),
                'secret': photoset.get('secret'),
                'server': photoset.get('server'),
                'farm': photoset.get('farm')
            })
    metadata['albums'] = albums
    
    # Note: get_photo_stats requires OAuth authentication
    # We're already capturing view count from the photo info above
    
    # Save metadata
    save_json(metadata, os.path.join(photo_dir, 'metadata.json'))
    
    # Get and save comments with user info
    comments_data = get_photo_comments(photo_id)
    comments = []
    if 'comments' in comments_data and 'comment' in comments_data['comments']:
        for comment in comments_data['comments']['comment']:
            author_id = comment.get('author')
            comment_obj = {
                'id': comment.get('id'),
                'author': author_id,
                'author_name': comment.get('authorname'),
                'date_created': comment.get('datecreate'),
                'permalink': comment.get('permalink'),
                'text': comment.get('_content', '')
            }
            
            # Add user info if we have an author
            if author_id:
                user_info = get_cached_user_info(author_id)
                comment_obj['author_avatar_url'] = user_info['avatar_url']
                comment_obj['author_is_pro'] = user_info['is_pro']
                comment_obj['author_display_name'] = user_info['display_name']
            
            comments.append(comment_obj)
    save_json(comments, os.path.join(photo_dir, 'comments.json'))
    
    # Get and save favorites with user info
    faves_data = get_photo_favorites(photo_id)
    favorites = []
    if 'photo' in faves_data and 'person' in faves_data['photo']:
        for person in faves_data['photo']['person']:
            nsid = person.get('nsid')
            fav_obj = {
                'nsid': nsid,
                'username': person.get('username'),
                'favedate': person.get('favedate')
            }
            
            # Add user info
            if nsid:
                user_info = get_cached_user_info(nsid)
                fav_obj['display_name'] = user_info['display_name']
                fav_obj['realname'] = user_info['realname']
                fav_obj['avatar_url'] = user_info['avatar_url']
                fav_obj['is_pro'] = user_info['is_pro']
                fav_obj['profile_url'] = user_info['profile_url']
            
            favorites.append(fav_obj)
    save_json(favorites, os.path.join(photo_dir, 'favorites.json'))
    
    # Get and save EXIF data
    exif_data = get_photo_exif(photo_id)
    exif = []
    if 'photo' in exif_data and 'exif' in exif_data['photo']:
        for item in exif_data['photo']['exif']:
            exif.append({
                'tag': item.get('tag'),
                'label': item.get('label'),
                'raw': item.get('raw', {}).get('_content', '')
            })
    save_json(exif, os.path.join(photo_dir, 'exif.json'))
    
    # Check if this is a video
    is_video = info['photo'].get('media', 'photo') == 'video'
    
    if is_video:
        print(f"    This is a video - attempting to download")
        
        # For videos, we need to get the video page URL and note it
        video_urls = []
        if 'urls' in info['photo'] and 'url' in info['photo']['urls']:
            for url in info['photo']['urls']['url']:
                if url.get('type') == 'photopage':
                    video_urls.append(url.get('_content'))
        
        # Get sizes - for videos this usually contains poster frames
        sizes = get_photo_sizes(photo_id)
        
        # Videos often don't have downloadable sources via the API
        # Save the largest thumbnail as a poster frame
        if sizes['sizes']['size']:
            sorted_sizes = sorted(
              sizes['sizes']['size'],
              key=lambda s: int(s.get('width') or 0),
              reverse=True
            )
            if sorted_sizes:
                thumb = sorted_sizes[0]
                thumb_url = thumb['source']
                thumb_path = os.path.join(photo_dir, 'poster.jpg')
                if download_photo(thumb_url, thumb_path):
                    print(f"    Downloaded video poster frame")
        
        # Save video metadata including the Flickr URL for manual download
        video_info = {
            'is_video': True,
            'video_urls': video_urls,
            'note': 'Videos must be downloaded manually from Flickr',
            'all_sizes': sizes['sizes']['size']
        }
        save_json(video_info, os.path.join(photo_dir, 'sizes.json'))
        
        # Also note in metadata
        metadata['video_info'] = {
            'download_note': 'Video file must be downloaded manually from Flickr',
            'flickr_urls': video_urls
        }
    else:
        # Download original photo
        sizes = get_photo_sizes(photo_id)
        original = None
        
        # Try to find original size, fallback to largest available
        for size in sizes['sizes']['size']:
            if size['label'] == 'Original':
                original = size
                break
        
        if not original and sizes['sizes']['size']:
            # Get the largest size available, handling missing width values
            sorted_sizes = sorted(
                sizes['sizes']['size'], 
                key=lambda s: int(s.get('width', 0)), 
                reverse=True
            )
            original = sorted_sizes[0] if sorted_sizes else None
        
        if original:
            photo_url = original['source']
            # Determine file extension from URL
            ext = photo_url.split('.')[-1].split('?')[0]
            if ext not in ['jpg', 'jpeg', 'png', 'gif']:
                ext = 'jpg'
            
            photo_path = os.path.join(photo_dir, f'original.{ext}')
            if download_photo(photo_url, photo_path):
                print(f"    Downloaded photo")
            
            # Save size info
            save_json({
                'original': original,
                'all_sizes': sizes['sizes']['size']
            }, os.path.join(photo_dir, 'sizes.json'))
    
    # Mark as complete
    with open(os.path.join(photo_dir, 'complete.flag'), 'w') as f:
        f.write(datetime.now().isoformat())
    
    # Be nice to Flickr's servers
    time.sleep(0.5)

def download_my_photos():
    print(f"\nDownloading photos for user {USER_ID}")
    processed_ids = set(os.listdir(PHOTOS_DIR))
    page = 1
    total_processed = 0

    while True:
        print(f"\nFetching page {page}...")
        photos_data = get_photos(USER_ID, page=page, per_page=100)
        photos = photos_data['photos']['photo']

        if not photos:
            break

        print(f"Found {len(photos)} photos on page {page}")

        for i, photo in enumerate(photos, 1):
            photo_id = photo['id']
            if photo_id in processed_ids:
                continue

            print(f"\n[{total_processed + i}/{photos_data['photos']['total']}]", end='')
            process_photo(photo, PHOTOS_DIR)

        total_processed += len(photos)

        if page >= photos_data['photos']['pages']:
            break
        page += 1

    print(f"\nCompleted downloading {total_processed} photos")


def download_favorites():
    """Download all favorited photos"""
    print(f"\nDownloading favorited photos for user {USER_ID}")
    page = 1
    total_processed = 0
    
    while True:
        print(f"\nFetching favorites page {page}...")
        faves_data = get_favorites(USER_ID, page=page, per_page=100)
        photos = faves_data['photos']['photo']
        
        if not photos:
            break
        
        print(f"Found {len(photos)} favorites on page {page}")
        
        for i, photo in enumerate(photos, 1):
            print(f"\n[Fav {total_processed + i}/{faves_data['photos']['total']}]", end='')
            process_photo(photo, FAVORITES_DIR, is_favorite=True)
        
        total_processed += len(photos)
        
        if page >= faves_data['photos']['pages']:
            break
        page += 1
    
    print(f"\nCompleted downloading {total_processed} favorited photos")

def create_index():
    """Create an index file for easy access"""
    print("\nCreating index files...")
    
    # Index for my photos
    my_photos_index = []
    if os.path.exists(PHOTOS_DIR):
        for photo_id in os.listdir(PHOTOS_DIR):
            metadata_path = os.path.join(PHOTOS_DIR, photo_id, 'metadata.json')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    my_photos_index.append({
                        'id': photo_id,
                        'title': metadata.get('title', ''),
                        'date_taken': metadata.get('date_taken', ''),
                        'date_uploaded': metadata.get('date_uploaded', ''),
                        'tags': metadata.get('tags', []),
                        'media': metadata.get('media', 'photo'),
                        'views': metadata.get('views', 0),
                        'albums': metadata.get('albums', [])
                    })
    
    save_json(my_photos_index, os.path.join(DATA_DIR, 'my_photos_index.json'))
    
    # Index for favorites
    favorites_index = []
    if os.path.exists(FAVORITES_DIR):
        for photo_id in os.listdir(FAVORITES_DIR):
            metadata_path = os.path.join(FAVORITES_DIR, photo_id, 'metadata.json')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    favorites_index.append({
                        'id': photo_id,
                        'title': metadata.get('title', ''),
                        'owner_name': metadata.get('owner_name', ''),
                        'date_taken': metadata.get('date_taken', ''),
                        'tags': metadata.get('tags', [])
                    })
    
    save_json(favorites_index, os.path.join(DATA_DIR, 'favorites_index.json'))
    
    # Create albums index
    print("Creating albums index...")
    albums_data = get_photosets(USER_ID)
    albums_index = []
    
    if 'photosets' in albums_data and 'photoset' in albums_data['photosets']:
        for album in albums_data['photosets']['photoset']:
            album_info = {
                'id': album.get('id'),
                'title': album.get('title', {}).get('_content', ''),
                'description': album.get('description', {}).get('_content', ''),
                'primary': album.get('primary'),
                'photos': album.get('photos'),
                'videos': album.get('videos'),
                'count_photos': album.get('count_photos'),
                'count_videos': album.get('count_videos'),
                'date_create': album.get('date_create'),
                'date_update': album.get('date_update')
            }
            albums_index.append(album_info)
    
    save_json(albums_index, os.path.join(DATA_DIR, 'albums_index.json'))
    
    print(f"Created index for {len(my_photos_index)} photos, {len(favorites_index)} favorites, and {len(albums_index)} albums")
    
    # Save user cache
    if USER_CACHE:
        save_json(USER_CACHE, os.path.join(DATA_DIR, 'users_cache.json'))
        print(f"Saved info for {len(USER_CACHE)} users to users_cache.json")

if __name__ == '__main__':
    print("Flickr Archive Downloader")
    print("=" * 50)
    
    # Create directories
    os.makedirs(PHOTOS_DIR, exist_ok=True)
    os.makedirs(FAVORITES_DIR, exist_ok=True)
    
    # Download everything
    download_my_photos()
    download_favorites()
    create_index()
    
    print("\nArchive complete!")
    print(f"Data saved to: {DATA_DIR}")