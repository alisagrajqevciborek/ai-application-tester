"""
Screenshot annotation utilities for highlighting issues in test screenshots.
"""
from PIL import Image, ImageDraw, ImageFont
import io
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class ScreenshotAnnotator:
    """Annotate screenshots with issue highlights and labels."""
    
    def __init__(self):
        self.highlight_color = (255, 0, 0)  # Red
        self.highlight_width = 4
        self.label_bg_color = (255, 0, 0, 220)  # Semi-transparent red
        self.label_text_color = (255, 255, 255)  # White
        self.padding = 50  # Padding around highlighted element when cropping
        
    def annotate_screenshot(
        self,
        screenshot_bytes: bytes,
        element_box: Optional[Dict] = None,
        label: Optional[str] = None,
        crop_to_element: bool = False
    ) -> bytes:
        """
        Annotate a screenshot with highlighting and labels.
        
        Args:
            screenshot_bytes: Original screenshot as bytes
            element_box: Dict with 'x', 'y', 'width', 'height' of element to highlight
            label: Text label to add above the highlighted element
            crop_to_element: If True, crop image to show just the element + padding
            
        Returns:
            Annotated screenshot as bytes
        """
        try:
            # Load image
            img = Image.open(io.BytesIO(screenshot_bytes))
            
            if element_box:
                # Draw highlight rectangle
                img = self._draw_highlight(img, element_box, label)
                
                # Crop to element if requested
                if crop_to_element:
                    img = self._crop_to_element(img, element_box)
            
            # Convert back to bytes
            output = io.BytesIO()
            img.save(output, format='PNG')
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error annotating screenshot: {e}")
            return screenshot_bytes  # Return original on error
    
    def _draw_highlight(
        self,
        img: Image.Image,
        element_box: Dict,
        label: Optional[str] = None
    ) -> Image.Image:
        """Draw a red rectangle around the element and add label."""
        draw = ImageDraw.Draw(img, 'RGBA')
        
        x = element_box['x']
        y = element_box['y']
        width = element_box['width']
        height = element_box['height']
        
        # Draw red rectangle around element
        draw.rectangle(
            [x, y, x + width, y + height],
            outline=self.highlight_color,
            width=self.highlight_width
        )
        
        # Add corner markers for extra visibility
        marker_size = 15
        # Top-left corner
        draw.line([x, y, x + marker_size, y], fill=self.highlight_color, width=self.highlight_width)
        draw.line([x, y, x, y + marker_size], fill=self.highlight_color, width=self.highlight_width)
        # Top-right corner
        draw.line([x + width - marker_size, y, x + width, y], fill=self.highlight_color, width=self.highlight_width)
        draw.line([x + width, y, x + width, y + marker_size], fill=self.highlight_color, width=self.highlight_width)
        # Bottom-left corner
        draw.line([x, y + height - marker_size, x, y + height], fill=self.highlight_color, width=self.highlight_width)
        draw.line([x, y + height, x + marker_size, y + height], fill=self.highlight_color, width=self.highlight_width)
        # Bottom-right corner
        draw.line([x + width - marker_size, y + height, x + width, y + height], fill=self.highlight_color, width=self.highlight_width)
        draw.line([x + width, y + height - marker_size, x + width, y + height], fill=self.highlight_color, width=self.highlight_width)
        
        # Add label if provided
        if label:
            img = self._add_label(img, x, y, label)
        
        return img
    
    def _add_label(
        self,
        img: Image.Image,
        x: float,
        y: float,
        label: str
    ) -> Image.Image:
        """Add a text label above the highlighted element."""
        draw = ImageDraw.Draw(img, 'RGBA')
        
        # Try to load a font, fall back to default if not available
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except:
            font = ImageFont.load_default()
        
        # Calculate label size
        bbox = draw.textbbox((0, 0), label, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Position label above element (or below if too close to top)
        label_padding = 8
        label_y = y - text_height - label_padding - 10
        if label_y < 0:
            label_y = y + 10  # Place below if too close to top
        
        label_x = x
        
        # Draw background rectangle for label
        bg_rect = [
            label_x - label_padding,
            label_y - label_padding,
            label_x + text_width + label_padding,
            label_y + text_height + label_padding
        ]
        draw.rectangle(bg_rect, fill=self.label_bg_color)
        
        # Draw text
        draw.text((label_x, label_y), label, fill=self.label_text_color, font=font)
        
        return img
    
    def _crop_to_element(
        self,
        img: Image.Image,
        element_box: Dict
    ) -> Image.Image:
        """Crop image to show element with padding."""
        x = element_box['x']
        y = element_box['y']
        width = element_box['width']
        height = element_box['height']
        
        # Calculate crop box with padding
        crop_x1 = max(0, x - self.padding)
        crop_y1 = max(0, y - self.padding)
        crop_x2 = min(img.width, x + width + self.padding)
        crop_y2 = min(img.height, y + height + self.padding)
        
        # Crop image
        cropped = img.crop((crop_x1, crop_y1, crop_x2, crop_y2))
        
        return cropped
    
    def create_comparison_screenshot(
        self,
        before_bytes: bytes,
        after_bytes: bytes
    ) -> bytes:
        """
        Create a side-by-side comparison of two screenshots.
        
        Args:
            before_bytes: Screenshot before interaction
            after_bytes: Screenshot after interaction
            
        Returns:
            Combined screenshot showing before/after
        """
        try:
            before_img = Image.open(io.BytesIO(before_bytes))
            after_img = Image.open(io.BytesIO(after_bytes))
            
            # Resize if needed to match heights
            if before_img.height != after_img.height:
                target_height = min(before_img.height, after_img.height)
                before_img = before_img.resize(
                    (int(before_img.width * target_height / before_img.height), target_height)
                )
                after_img = after_img.resize(
                    (int(after_img.width * target_height / after_img.height), target_height)
                )
            
            # Create new image with both screenshots side by side
            total_width = before_img.width + after_img.width + 10  # 10px gap
            combined = Image.new('RGB', (total_width, before_img.height), (255, 255, 255))
            
            # Paste images
            combined.paste(before_img, (0, 0))
            combined.paste(after_img, (before_img.width + 10, 0))
            
            # Add labels
            draw = ImageDraw.Draw(combined)
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except:
                font = ImageFont.load_default()
            
            draw.text((10, 10), "BEFORE", fill=(0, 0, 0), font=font)
            draw.text((before_img.width + 20, 10), "AFTER", fill=(0, 0, 0), font=font)
            
            # Convert to bytes
            output = io.BytesIO()
            combined.save(output, format='PNG')
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error creating comparison screenshot: {e}")
            return before_bytes  # Return original on error
