#!/usr/bin/env python3
"""
Manager for Sora-generated images from Explore gallery.
This module handles downloading images from sora.chatgpt.com/explore/images
"""
import os
import json
import random
import shutil
import time
import requests
from pathlib import Path
from typing import List, Dict, Optional

class SoraImageManager:
    """Manages Sora images from explore gallery."""
    
    def __init__(self, sora_dir: str = None):
        """
        Initialize the Sora image manager.
        
        Args:
            sora_dir: Path to directory containing Sora images. 
                     Defaults to kids/static/img/sora
        """
        if sora_dir is None:
            # Default to kids/static/img/sora
            base = Path(__file__).parent.parent
            sora_dir = base / "static" / "img" / "sora"
        
        self.sora_dir = Path(sora_dir)
        self.sora_dir.mkdir(parents=True, exist_ok=True)
        self.explore_url = "https://sora.chatgpt.com/explore/images"
    
    def fetch_sora_explore_images(self, count: int = 20, keywords: List[str] = None) -> List[Dict[str, str]]:
        """
        Fetch images from Sora Explore gallery using API or web scraping.
        
        Args:
            count: Number of images to fetch
            keywords: Optional keywords to filter images
            
        Returns:
            List of image dicts with URL and metadata
        """
        try:
            print(f"🔍 Pobieram obrazy z Sora Explore (limit: {count})...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
            }
            
            # Try to fetch the page
            response = requests.get(self.explore_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Simple regex-based extraction for image URLs
            import re
            
            # Pattern for image URLs (adjust based on actual site structure)
            # Looking for URLs that contain image formats
            url_pattern = r'https://[^\s"\'<>]+?\.(?:jpg|jpeg|png|webp)[^\s"\'<>]*'
            found_urls = re.findall(url_pattern, response.text)
            
            # Deduplicate and filter
            seen = set()
            images = []
            
            for url in found_urls:
                if url in seen:
                    continue
                seen.add(url)
                
                # Skip small icons, logos, etc.
                if any(x in url.lower() for x in ['icon', 'logo', 'avatar', 'favicon', 'thumb']):
                    continue
                
                images.append({
                    'url': url,
                    'source': 'Sora Explore',
                    'keywords': keywords or []
                })
                
                if len(images) >= count:
                    break
            
            if images:
                print(f"✓ Znaleziono {len(images)} obrazów")
            else:
                print(f"⚠️  Nie znaleziono obrazów na stronie")
                print(f"   Możesz ręcznie dodać obrazy z: {self.explore_url}")
            
            return images
            
        except Exception as e:
            print(f"⚠️  Błąd pobierania z Sora Explore: {e}")
            print(f"   Spróbuję użyć lokalnej biblioteki...")
            return []
    
    def download_image_from_url(self, url: str, filename: str = None) -> Optional[str]:
        """
        Download a single image from URL.
        
        Args:
            url: Image URL
            filename: Optional filename (auto-generated if None)
            
        Returns:
            Path to downloaded image or None on failure
        """
        try:
            if filename is None:
                timestamp = int(time.time())
                random_suffix = random.randint(1000, 9999)
                ext = 'jpg'
                # Try to get extension from URL
                url_ext = url.split('.')[-1].split('?')[0].lower()
                if url_ext in ['jpg', 'jpeg', 'png', 'webp']:
                    ext = url_ext
                filename = f"sora_{timestamp}_{random_suffix}.{ext}"
            
            filepath = self.sora_dir / filename
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://sora.chatgpt.com/'
            }
            
            response = requests.get(url, headers=headers, timeout=30, stream=True)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Verify file was created and has content
            if filepath.exists() and filepath.stat().st_size > 1000:  # at least 1KB
                return str(filepath)
            else:
                if filepath.exists():
                    filepath.unlink()
                return None
            
        except Exception as e:
            print(f"✗ Błąd pobierania obrazu z {url[:50]}...: {e}")
            return None
    
    def populate_sora_library(self, count: int = 20) -> int:
        """
        Download images from Sora Explore to local library.
        
        Args:
            count: Number of images to download
            
        Returns:
            Number of successfully downloaded images
        """
        print(f"\n📥 Pobieram {count} obrazów z Sora Explore do biblioteki...")
        print(f"   Źródło: {self.explore_url}\n")
        
        images = self.fetch_sora_explore_images(count)
        
        if not images:
            print("\n⚠️  Nie znaleziono obrazów do pobrania")
            print("   Możesz ręcznie:")
            print(f"   1. Odwiedzić: {self.explore_url}")
            print(f"   2. Pobrać obrazy i dodać do: {self.sora_dir}")
            return 0
        
        downloaded = 0
        for i, img_info in enumerate(images):
            url = img_info['url']
            filename = f"sora_explore_{i + 1}.jpg"
            
            print(f"  [{i+1}/{len(images)}] Pobieram obraz...")
            result = self.download_image_from_url(url, filename)
            
            if result:
                # Save metadata
                meta = {
                    'source': 'Sora Explore',
                    'source_url': self.explore_url,
                    'image_url': url,
                    'keywords': img_info.get('keywords', []),
                    'downloaded_at': time.time()
                }
                
                meta_path = Path(result).with_suffix('.json')
                with open(meta_path, 'w', encoding='utf-8') as f:
                    json.dump(meta, f, ensure_ascii=False, indent=2)
                
                downloaded += 1
                print(f"    ✓ Zapisano: {filename}")
            
            time.sleep(1)  # Rate limiting - be nice to the server
        
        print(f"\n✓ Pobrano {downloaded}/{len(images)} obrazów do: {self.sora_dir}")
        return downloaded
    
    def list_available_images(self) -> List[Dict[str, str]]:
        """
        List all available Sora images in local library.
        
        Returns:
            List of dicts with image info (path, filename, description)
        """
        images = []
        for ext in ['jpg', 'jpeg', 'png', 'webp']:
            for img_file in self.sora_dir.glob(f"*.{ext}"):
                if img_file.is_file():
                    # Check for metadata JSON
                    meta_file = img_file.with_suffix('.json')
                    description = ""
                    if meta_file.exists():
                        try:
                            with open(meta_file, 'r', encoding='utf-8') as f:
                                meta = json.load(f)
                                description = meta.get('description', meta.get('source', ''))
                        except Exception:
                            pass
                    
                    images.append({
                        'path': str(img_file),
                        'filename': img_file.name,
                        'description': description
                    })
        
        return images
    
    def get_images_for_article(self, topic: str, slug: str, count: int = 4, 
                               output_dir: str = None) -> List[Dict[str, str]]:
        """
        Get images for an article from local Sora library.
        If library is empty, try to populate it first.
        
        Args:
            topic: Article topic
            slug: Article slug for directory name
            count: Number of images needed
            output_dir: Where to copy images
            
        Returns:
            List of dicts with image info (filename, description, path)
        """
        # Check if we have local images
        available = self.list_available_images()
        
        # If library is empty, try to populate it
        if not available:
            print(f"\n📚 Biblioteka Sora jest pusta. Pobieram obrazy...")
            downloaded = self.populate_sora_library(count=min(count * 3, 20))
            if downloaded > 0:
                available = self.list_available_images()
        
        if not available:
            print(f"\n⚠️  Brak obrazów Sora")
            print(f"   Uruchom: python kids/tools/sora_image_manager.py populate {count}")
            print(f"   lub ręcznie dodaj obrazy do: {self.sora_dir}")
            return []
        
        # Set up output directory
        if output_dir is None:
            base = Path(__file__).parent.parent
            output_dir = base / "static" / "img" / "generated" / slug
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Randomly select images
        selected = random.sample(available, min(count, len(available)))
        
        # Copy images to output directory
        result = []
        for i, img_info in enumerate(selected):
            src_path = Path(img_info['path'])
            dest_filename = f"img_sora_{i}{src_path.suffix}"
            dest_path = output_dir / dest_filename
            
            try:
                # Copy image
                shutil.copy2(src_path, dest_path)
                
                # Create metadata for the copied image
                meta = {
                    "provider": "Sora Explore",
                    "source": "sora.chatgpt.com/explore/images",
                    "description": img_info.get('description', topic),
                    "original_filename": img_info['filename'],
                    "license": "AI Generated via Sora",
                }
                
                meta_path = dest_path.with_suffix('.json')
                with open(meta_path, 'w', encoding='utf-8') as f:
                    json.dump(meta, f, ensure_ascii=False, indent=2)
                
                result.append({
                    'filename': dest_filename,
                    'description': topic,
                    'photographer': 'Sora AI'
                })
                
                print(f"✓ Użyto obrazu Sora: {dest_filename}")
                
            except Exception as e:
                print(f"✗ Błąd kopiowania obrazu {img_info['filename']}: {e}")
                continue
        
        return result
    
    def add_image_with_metadata(self, image_path: str, description: str = "", 
                                keywords: List[str] = None) -> bool:
        """
        Add an image to the Sora library with metadata.
        
        Args:
            image_path: Path to the image file to add
            description: Description of the image
            keywords: Optional list of keywords for the image
            
        Returns:
            True if successful, False otherwise
        """
        try:
            src = Path(image_path)
            if not src.exists():
                print(f"✗ Obraz nie istnieje: {image_path}")
                return False
            
            # Copy to Sora directory
            dest = self.sora_dir / src.name
            shutil.copy2(src, dest)
            
            # Create metadata
            meta = {
                "description": description,
                "keywords": keywords or [],
                "source": "Manually added",
                "added_at": time.time()
            }
            
            meta_path = dest.with_suffix('.json')
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
            
            print(f"✓ Dodano obraz: {dest.name}")
            return True
            
        except Exception as e:
            print(f"✗ Błąd dodawania obrazu: {e}")
            return False


def main():
    """CLI for managing Sora images."""
    import sys
    
    manager = SoraImageManager()
    
    if len(sys.argv) < 2:
        print("Sora Image Manager - Obrazy z Explore")
        print("=" * 50)
        print("\nUsage:")
        print("  python sora_image_manager.py list")
        print("  python sora_image_manager.py populate [count]")
        print("  python sora_image_manager.py add <image_path> [description]")
        print("  python sora_image_manager.py test '<topic>' '<slug>'")
        print(f"\nSora directory: {manager.sora_dir}")
        print(f"Explore URL: {manager.explore_url}")
        return
    
    command = sys.argv[1].lower()
    
    if command == "list":
        images = manager.list_available_images()
        print(f"\n📚 Lokalna biblioteka Sora:")
        print(f"   Lokalizacja: {manager.sora_dir}")
        print(f"   Liczba obrazów: {len(images)}\n")
        if images:
            for img in images:
                print(f"  ✓ {img['filename']}")
                if img['description']:
                    print(f"    {img['description']}")
        else:
            print("  (pusta)")
            print(f"\n  Uruchom: python sora_image_manager.py populate 20")
    
    elif command == "populate":
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        manager.populate_sora_library(count)
        
    elif command == "add" and len(sys.argv) >= 3:
        image_path = sys.argv[2]
        description = sys.argv[3] if len(sys.argv) > 3 else ""
        manager.add_image_with_metadata(image_path, description)
        
    elif command == "test" and len(sys.argv) >= 4:
        topic = sys.argv[2]
        slug = sys.argv[3]
        print(f"\nTest: Wybieranie obrazów dla artykułu")
        print(f"  Temat: {topic}")
        print(f"  Slug: {slug}\n")
        images = manager.get_images_for_article(topic, slug, count=4)
        print(f"\n✓ Wybrano {len(images)} obrazów:")
        for img in images:
            print(f"  - {img['filename']}")
    
    else:
        print("Nieprawidłowa komenda. Użyj: list, populate, add, lub test")


if __name__ == "__main__":
    main()
