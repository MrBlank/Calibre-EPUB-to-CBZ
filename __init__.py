from calibre.customize.conversion import OutputFormatPlugin
from calibre.ptempfile import TemporaryDirectory
from calibre.utils.zipfile import ZipFile
from os import path
from lxml import etree
import re


class EPUBToCBZ(OutputFormatPlugin):
    name = "EPUB to CBZ"
    author = "Josh Nichols"
    version = (1, 0, 0)
    file_type = "cbz"
    commit_name = "cbz_output"

    def convert(self, oeb_book, output_path, input_plugin, opts, log):
        cbz = ZipFile(output_path, mode="w")

        # Handle cover image first
        cover_image = None
        potential_covers = []

        # Method 1: Try manifest properties (EPUB3)
        for item in oeb_book.manifest:
            if hasattr(item, 'properties') and 'cover-image' in item.properties:
                potential_covers.append(('manifest_property', item))
                if not cover_image:  # Take the first one as primary cover
                    cover_image = item
        
        # Method 2: Try metadata (EPUB2)
        if not cover_image and hasattr(oeb_book, 'metadata'):
            # Look for <meta name="cover" content="cover-id"/>
            cover_id = None
            for metadata in oeb_book.metadata:
                if hasattr(metadata, 'iterchildren'):
                    for meta in metadata.iterchildren():
                        if hasattr(meta, 'get') and meta.get('name') == 'cover':
                            cover_id = meta.get('content')
                            break
                    if cover_id:
                        break
            
            if cover_id:
                for item in oeb_book.manifest:
                    if hasattr(item, 'id') and item.id == cover_id:
                        potential_covers.append(('metadata', item))
                        if not cover_image:  # Take the first one as primary cover
                            cover_image = item

        # Method 3: Try guide references (EPUB2)
        if not cover_image and hasattr(oeb_book, 'guide'):
            for ref in oeb_book.guide:
                if (hasattr(ref, 'type') and 
                    hasattr(ref, 'href') and 
                    ref.type and 
                    ref.type.lower() == 'cover'):
                    # The guide points to an XHTML file, need to extract image from it
                    href = ref.href.split('#')[0]  # Remove fragment identifier if any
                    xhtml_item = oeb_book.manifest.hrefs.get(href)
                    if xhtml_item and hasattr(xhtml_item, 'data'):
                        # Look for the first image in this XHTML file
                        for img in xhtml_item.data.xpath('//img | //xhtml:img', namespaces={'xhtml': 'http://www.w3.org/1999/xhtml'}):
                            src = img.get('src')
                            if src:
                                if not src.startswith('/'):
                                    src = path.normpath(path.join(path.dirname(href), src))
                                img_item = oeb_book.manifest.hrefs.get(src)
                                if img_item and img_item.media_type.startswith('image'):
                                    potential_covers.append(('guide', img_item))
                                    if not cover_image:  # Take the first one as primary cover
                                        cover_image = img_item
                    break

        # Method 4: Try item ID conventions and manifest items
        if not cover_image:
            for item in oeb_book.manifest:
                # Check if it's an image and either has 'cover' in id/href or is the only image in manifest
                if (item.media_type.startswith('image') and
                    hasattr(item, 'id') and
                    (
                        # Has 'cover' in id/href
                        ('cover' in item.id.lower() or
                         (hasattr(item, 'href') and 'cover' in item.href.lower()) or
                         # Special case: if this is the only image in the manifest, it's likely the cover
                         len([x for x in oeb_book.manifest if hasattr(x, 'media_type') and 
                              x.media_type.startswith('image')]) == 1
                        )
                    )):
                    potential_covers.append(('id_convention', item))
                    if not cover_image:  # Take the first one as primary cover
                        cover_image = item
                    break
            
            # Log warning if multiple potential covers found
            if len(potential_covers) > 1:
                oeb_book.logger.warning(f"Found {len(potential_covers)} potential cover images:")
                for method, item in potential_covers:
                    oeb_book.logger.warning(f"  - {method}: {item.href}")
                oeb_book.logger.warning(f"Using {potential_covers[0][1].href} as the cover image.")

        with TemporaryDirectory('_img_extract_') as tdir:
            page_num = 1
            processed_images = set()  # Keep track of processed images by href

            # Process cover image first if found
            if cover_image:
                oeb_book.logger.info("Processing cover image:", cover_image.href)
                basename = f"page_{page_num:03d}_cover{path.splitext(cover_image.href)[1]}"
                tmp_file = path.join(tdir, basename)
                with open(tmp_file, "wb") as binary_file:
                    binary_file.write(cover_image.data)
                cbz.write(tmp_file, basename)
                page_num += 1
                processed_images.add(cover_image.href)

            # Get spine items in reading order
            spine_items = []
            oeb_book.logger.info(f"Found {len(oeb_book.spine)} spine items")
            for item in oeb_book.spine:
                item_id = item.id if hasattr(item, 'id') else 'unknown'
                item_href = item.href if hasattr(item, 'href') else str(item)
                oeb_book.logger.info(f"Processing spine item: id='{item_id}' href='{item_href}'")
                if isinstance(item, str):
                    item = oeb_book.manifest.hrefs[item]
                    item_id = item.id if hasattr(item, 'id') else 'unknown'
                    item_href = item.href if hasattr(item, 'href') else str(item)
                    oeb_book.logger.info(f"  - Resolved to manifest item: id='{item_id}' href='{item_href}'")
                spine_items.append(item)

            # Process images in reading order
            for item in spine_items:
                if hasattr(item, 'data'):
                    # Find all img tags and SVG image tags in the XHTML
                    oeb_book.logger.info(f"Looking for images in {item.href}")
                    try:
                        # Try standard img tags first
                        for img in item.data.xpath('//img | //xhtml:img', namespaces={'xhtml': 'http://www.w3.org/1999/xhtml'}):
                            oeb_book.logger.info(f"Found img tag in {item.href}")
                            src = img.get('src')
                            if src:
                                # Handle relative paths
                                if not src.startswith('/'):
                                    # First try relative to current directory
                                    src_try = path.join(path.dirname(item.href), src)
                                    img_item = oeb_book.manifest.hrefs.get(src_try)
                                    if not img_item:
                                        # If not found, try normalizing the path
                                        src_try = path.normpath(path.join(path.dirname(item.href), src))
                                        img_item = oeb_book.manifest.hrefs.get(src_try)
                                        if not img_item:
                                            # If still not found, try the raw src
                                            img_item = oeb_book.manifest.hrefs.get(src)
                                else:
                                    img_item = oeb_book.manifest.hrefs.get(src)
                                
                                oeb_book.logger.info(f"Found image source: {src}")
                                # Only process raster image types supported by CBZ
                                if (img_item and 
                                    img_item.media_type in ['image/jpeg', 'image/png', 'image/gif'] and
                                    img_item.href not in processed_images):
                                    basename = f"page_{page_num:03d}{path.splitext(img_item.href)[1]}"
                                    oeb_book.logger.info(f"Saving as: {basename}")
                                    tmp_file = path.join(tdir, basename)
                                    with open(tmp_file, "wb") as binary_file:
                                        binary_file.write(img_item.data)
                                    cbz.write(tmp_file, basename)
                                    page_num += 1
                                    processed_images.add(img_item.href)
                                else:
                                    oeb_book.logger.warning(f"Image not found in manifest or not an image: {src}")

                    except Exception as e:
                        oeb_book.logger.error(f"Error processing {item.href}: {e}")

        cbz.close()