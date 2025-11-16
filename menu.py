import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame
import sys
import threading
from youtube import suggest_youtube_videos

# Window dimensions
WINDOW_WIDTH = 740
WINDOW_HEIGHT = 720

class MainMenu:
    def __init__(self):
        pygame.init()
        
        pygame.display.set_caption("RhythmGen - Main Menu")
        display_info = pygame.display.Info()
        display_w = display_info.current_w or WINDOW_WIDTH
        display_h = display_info.current_h or WINDOW_HEIGHT
        self.display_size = (display_w, display_h)
        
        try:
            self.display_surface = pygame.display.set_mode(self.display_size, pygame.FULLSCREEN)
        except pygame.error:
            # Fallback to windowed mode if fullscreen fails
            self.display_surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
            self.display_size = (WINDOW_WIDTH, WINDOW_HEIGHT)
        
        # Logical rendering surface
        self.screen = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT)).convert()
        
        # Fonts
        self.title_font_size = 120
        self.title_font = pygame.font.Font(None, self.title_font_size)
        self.subtitle_font_size = 36
        self.subtitle_font = pygame.font.Font(None, self.subtitle_font_size)
        self.button_font_size = 48
        self.button_font = pygame.font.Font(None, self.button_font_size)
        self.instructions_title_font_size = 64
        self.instructions_title_font = pygame.font.Font(None, self.instructions_title_font_size)
        self.instructions_font_size = 32
        self.instructions_font = pygame.font.Font(None, self.instructions_font_size)
        
        # Animation
        self.frame_count = 0
        
        # Text overlays for scaling
        self._text_overlays = []
        
        # State
        self.showing_instructions = False
        self.showing_url_input = False
        self.showing_loading = False  # Loading screen state
        self.loading_message = ""  # Message to display while loading
        self.url_input_text = ""
        self.search_results = []  # List of video results from search
        self.selected_video_index = -1  # Currently selected video in dropdown
        self.search_scroll = 0  # Scroll offset for search results
        self.is_searching = False  # Flag to show loading state
        self.search_thread = None  # Background thread for search
        self.instructions_scroll = 0  # Scroll offset for instructions
        self.max_instructions_scroll = 0  # Maximum scroll value
        
        # Create gradient background
        self.background = self._create_vertical_gradient((25, 10, 50), (5, 5, 10))
    
    def _create_vertical_gradient(self, top_color, bottom_color):
        surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        for y in range(WINDOW_HEIGHT):
            t = y / WINDOW_HEIGHT
            r = int(top_color[0] * (1 - t) + bottom_color[0] * t)
            g = int(top_color[1] * (1 - t) + bottom_color[1] * t)
            b = int(top_color[2] * (1 - t) + bottom_color[2] * t)
            pygame.draw.line(surf, (r, g, b), (0, y), (WINDOW_WIDTH, y))
        return surf
    
    def _get_scale_and_offset(self):
        """Calculate the current scale and offset for the display."""
        display_w, display_h = self.display_size
        scale_to_height = display_h / WINDOW_HEIGHT
        scaled_w = int(round(WINDOW_WIDTH * scale_to_height))
        
        use_height_scaling = scaled_w <= display_w and scale_to_height > 0
        
        if not use_height_scaling:
            scale = display_w / WINDOW_WIDTH
            scaled_w = display_w
            scaled_h = int(round(WINDOW_HEIGHT * scale))
        else:
            scale = scale_to_height
            scaled_h = display_h
        
        offset_x = (display_w - scaled_w) // 2
        offset_y = (display_h - scaled_h) // 2
        
        return scale, offset_x, offset_y
    
    def _queue_text(self, overlay_list, font, text, color, x, y, *, center=False, alpha=255, font_size=None):
        overlay_list.append({
            "font": font,
            "text": text,
            "color": color,
            "x": x,
            "y": y,
            "center": center,
            "alpha": alpha,
            "font_size": font_size
        })
    
    def _draw_text_overlays(self, scale, offset_x, offset_y):
        for entry in self._text_overlays:
            font = entry["font"]
            text = entry["text"]
            color = entry["color"]
            alpha = entry["alpha"]
            font_size = entry.get("font_size")
            
            effective_font = font
            if scale != 1.0 and font_size:
                scaled_size = max(1, int(round(font_size * scale)))
                effective_font = pygame.font.Font(None, scaled_size)
            
            surf = effective_font.render(text, True, color)
            if alpha < 255:
                surf = surf.copy()
                surf.set_alpha(alpha)
            
            draw_x = offset_x + entry["x"] * scale
            draw_y = offset_y + entry["y"] * scale
            
            if entry["center"]:
                draw_x -= surf.get_width() / 2
            draw_pos = (int(round(draw_x)), int(round(draw_y)))
            self.display_surface.blit(surf, draw_pos)
        
        pygame.display.flip()
    
    def _present_canvas(self):
        display_w, display_h = self.display_size
        scale_to_height = display_h / WINDOW_HEIGHT
        scaled_w = int(round(WINDOW_WIDTH * scale_to_height))
        scaled_h = display_h
        
        use_height_scaling = scaled_w <= display_w and scale_to_height > 0
        
        if not use_height_scaling:
            scale_to_width = display_w / WINDOW_WIDTH
            scaled_w = display_w
            scaled_h = int(round(WINDOW_HEIGHT * scale_to_width))
            scale = scale_to_width
        else:
            scale = scale_to_height
        
        import math
        integer_multiple = math.isclose(scale, round(scale)) and scale >= 1
        integer_multiple = integer_multiple or (
            scaled_w % WINDOW_WIDTH == 0 and scaled_h % WINDOW_HEIGHT == 0
        )
        
        if scaled_w == WINDOW_WIDTH and scaled_h == WINDOW_HEIGHT:
            canvas = self.screen
        elif integer_multiple:
            canvas = pygame.transform.scale(self.screen, (scaled_w, scaled_h))
        else:
            canvas = pygame.transform.smoothscale(self.screen, (scaled_w, scaled_h))
        
        offset_x = (display_w - scaled_w) // 2
        offset_y = (display_h - scaled_h) // 2
        
        self.display_surface.fill((0, 0, 0))
        self.display_surface.blit(canvas, (offset_x, offset_y))
        
        scale_factor = scaled_w / WINDOW_WIDTH if WINDOW_WIDTH else 1.0
        return scale_factor, offset_x, offset_y
    
    def _check_button_click(self, x, y):
        """Check if a click is on any menu button."""
        if self.showing_instructions:
            # Back button when showing instructions
            center_x = WINDOW_WIDTH / 2
            button_width = 300
            button_height = 70
            
            back_y = WINDOW_HEIGHT - 120
            back_rect = pygame.Rect(center_x - button_width / 2, back_y, button_width, button_height)
            
            if back_rect.collidepoint(x, y):
                return "back"
        elif self.showing_url_input:
            # Check if clicking on a search result
            if self.search_results:
                results_area_top = 220
                result_height = 80
                result_spacing = 10
                
                for i, video in enumerate(self.search_results[:5]):  # Show max 5 results
                    result_y = results_area_top + i * (result_height + result_spacing) - self.search_scroll
                    result_rect = pygame.Rect(70, result_y, WINDOW_WIDTH - 140, result_height)
                    
                    if result_rect.collidepoint(x, y) and result_y >= results_area_top and result_y + result_height <= WINDOW_HEIGHT - 150:
                        return ("select_video", i)
            
            # Search and Cancel buttons on URL input screen
            center_x = WINDOW_WIDTH / 2
            button_width = 250
            button_height = 70
            button_spacing = 30
            
            search_y = WINDOW_HEIGHT / 2 + 120 if not self.search_results else WINDOW_HEIGHT - 100
            search_rect = pygame.Rect(center_x - button_width - button_spacing / 2, search_y, button_width, button_height)
            
            cancel_y = search_y
            cancel_rect = pygame.Rect(center_x + button_spacing / 2, cancel_y, button_width, button_height)
            
            if search_rect.collidepoint(x, y):
                return "search"
            elif cancel_rect.collidepoint(x, y):
                return "cancel"
        else:
            # Main menu buttons
            center_x = WINDOW_WIDTH / 2
            button_width = 300
            button_height = 70
            button_spacing = 30
            
            # Calculate starting Y position for centered buttons
            total_height = (button_height * 3) + (button_spacing * 2)
            start_y = (WINDOW_HEIGHT / 2) - (total_height / 2) + 80
            
            play_rect = pygame.Rect(center_x - button_width / 2, start_y, button_width, button_height)
            howto_rect = pygame.Rect(center_x - button_width / 2, start_y + button_height + button_spacing, button_width, button_height)
            quit_rect = pygame.Rect(center_x - button_width / 2, start_y + (button_height + button_spacing) * 2, button_width, button_height)
            
            if play_rect.collidepoint(x, y):
                return "play"
            elif howto_rect.collidepoint(x, y):
                return "howto"
            elif quit_rect.collidepoint(x, y):
                return "quit"
        
        return None
    
    def _render_instructions(self):
        """Render the How To Play screen."""
        center_x = WINDOW_WIDTH / 2
        
        # Title (fixed at top)
        self._queue_text(
            self._text_overlays,
            self.instructions_title_font,
            "How To Play",
            (100, 255, 200),
            center_x,
            60,
            center=True,
            font_size=self.instructions_title_font_size
        )
        
        # Create a surface for scrollable content
        scroll_area_top = 140
        scroll_area_bottom = WINDOW_HEIGHT - 150  # Leave room for back button
        scroll_area_height = scroll_area_bottom - scroll_area_top
        
        # Instructions text
        instructions = [
            "Welcome to RhythmGen!",
            "",
            "Gameplay:",
            "• Notes will fall down the lanes from the top",
            "• Press the correct key when notes reach the white line",
            "• Perfect timing = Perfect hit (increases multiplier)",
            "• Good timing = Good hit (still increases combo)",
            "• Missing notes or wrong timing breaks your combo",
            "",
            "Scoring System:",
            "• Each note gives you points based on your multiplier",
            "• Build combos by hitting notes consecutively",
            "• Higher multiplier = more points per note",
            "• Get 5 Perfect hits in a row to increase multiplier",
            "• Maximum multiplier is 7x",
            "• Missing a note resets your multiplier to 1x",
            "",
            "Controls:",
            "• A = Lane 1 (leftmost)",
            "• S = Lane 2",
            "• D = Lane 3",
            "• F = Lane 4 (rightmost)",
            "• ESC = Pause/Unpause during gameplay",
            "",
            "Tips:",
            "• Watch the notes as they fall to prepare",
            "• Focus on timing over speed",
            "• The progress bar at the bottom shows song progress",
            "• Your accuracy is tracked in the sidebar",
            "• Aim for Perfect hits to maximize your score!",
            "",
            "Ready to play? Click Play from the main menu!",
        ]
        
        # Calculate total content height
        line_height = 36
        total_content_height = 0
        for line in instructions:
            if line == "":
                total_content_height += 15
            else:
                total_content_height += line_height
        
        # Update max scroll
        self.max_instructions_scroll = max(0, total_content_height - scroll_area_height)
        
        # Clamp scroll
        self.instructions_scroll = max(0, min(self.instructions_scroll, self.max_instructions_scroll))
        
        # Create clipping mask for scrollable area
        scroll_surface = pygame.Surface((WINDOW_WIDTH, scroll_area_height))
        scroll_surface.fill((0, 0, 0))  # Will be transparent where we draw
        scroll_surface.set_colorkey((0, 0, 0))
        
        # Draw instructions on scroll surface
        y_offset = -self.instructions_scroll
        for i, line in enumerate(instructions):
            if line == "":
                y_offset += 15
                continue
            
            # Different color for section headers
            if line.endswith(":"):
                color = (255, 255, 100)
            elif line == "Welcome to RhythmGen!" or "Ready to play?" in line:
                color = (255, 150, 255)
            else:
                color = (220, 220, 220)
            
            # Only render if visible in scroll area
            if -line_height <= y_offset <= scroll_area_height:
                text_surf = self.instructions_font.render(line, True, color)
                text_x = center_x - text_surf.get_width() / 2
                scroll_surface.blit(text_surf, (text_x, y_offset))
            
            y_offset += line_height
        
        # Blit scroll surface to screen
        self.screen.blit(scroll_surface, (0, scroll_area_top))
        
        # Draw scroll indicators if content is scrollable
        if self.max_instructions_scroll > 0:
            # Show scroll up indicator
            if self.instructions_scroll > 0:
                indicator_text = "▲ Scroll Up"
                indicator_surf = self.instructions_font.render(indicator_text, True, (150, 150, 200))
                self.screen.blit(indicator_surf, (center_x - indicator_surf.get_width() / 2, scroll_area_top - 30))
            
            # Show scroll down indicator
            if self.instructions_scroll < self.max_instructions_scroll:
                indicator_text = "▼ Scroll Down"
                indicator_surf = self.instructions_font.render(indicator_text, True, (150, 150, 200))
                self.screen.blit(indicator_surf, (center_x - indicator_surf.get_width() / 2, scroll_area_bottom + 5))
            
            # Draw scrollbar
            scrollbar_x = WINDOW_WIDTH - 30
            scrollbar_height = scroll_area_height - 20
            scrollbar_y = scroll_area_top + 10
            
            # Background track
            pygame.draw.rect(self.screen, (60, 60, 80), 
                           (scrollbar_x, scrollbar_y, 8, scrollbar_height), border_radius=4)
            
            # Thumb
            thumb_height = max(30, int((scroll_area_height / total_content_height) * scrollbar_height))
            thumb_y = scrollbar_y + int((self.instructions_scroll / self.max_instructions_scroll) * (scrollbar_height - thumb_height))
            pygame.draw.rect(self.screen, (150, 150, 200), 
                           (scrollbar_x - 2, thumb_y, 12, thumb_height), border_radius=6)
        
        # Back button
        button_width = 300
        button_height = 70
        back_y = WINDOW_HEIGHT - 120
        back_rect = pygame.Rect(center_x - button_width / 2, back_y, button_width, button_height)
        
        # Check hover
        mouse_pos = pygame.mouse.get_pos()
        scale, offset_x, offset_y = self._get_scale_and_offset()
        logical_mouse_x = (mouse_pos[0] - offset_x) / scale
        logical_mouse_y = (mouse_pos[1] - offset_y) / scale
        
        back_hover = back_rect.collidepoint(logical_mouse_x, logical_mouse_y)
        back_color = (100, 100, 200) if back_hover else (60, 60, 120)
        back_text_color = (255, 255, 255) if back_hover else (200, 200, 200)
        
        pygame.draw.rect(self.screen, back_color, back_rect, border_radius=12)
        pygame.draw.rect(self.screen, (150, 150, 255), back_rect, 3, border_radius=12)
        
        self._queue_text(
            self._text_overlays,
            self.button_font,
            "Back",
            back_text_color,
            center_x,
            back_y + button_height / 2 - 18,
            center=True,
            font_size=self.button_font_size
        )
    
    def _render_url_input(self):
        """Render the YouTube URL input screen."""
        center_x = WINDOW_WIDTH / 2
        center_y = WINDOW_HEIGHT / 2
        
        # Title
        title_text = "Search YouTube Videos"
        self._queue_text(
            self._text_overlays,
            self.instructions_title_font,
            title_text,
            (100, 255, 200),
            center_x,
            40,
            center=True,
            font_size=self.instructions_title_font_size
        )
        
        # Instructions
        if not self.search_results:
            self._queue_text(
                self._text_overlays,
                self.instructions_font,
                "Enter a search query to find videos:",
                (200, 200, 220),
                center_x,
                center_y - 120,
                center=True,
                font_size=self.instructions_font_size
            )
        
        # Input box
        input_width = 600
        input_height = 60
        input_x = center_x - input_width / 2
        input_y = 120 if self.search_results else center_y - 50
        input_rect = pygame.Rect(input_x, input_y, input_width, input_height)
        
        # Draw input box
        pygame.draw.rect(self.screen, (40, 40, 60), input_rect, border_radius=8)
        pygame.draw.rect(self.screen, (100, 200, 255), input_rect, 3, border_radius=8)
        
        # Draw text in input box
        if self.url_input_text:
            # Render the text
            text_surf = self.instructions_font.render(self.url_input_text, True, (255, 255, 255))
            
            # If text is too wide, show only the end portion
            if text_surf.get_width() > input_width - 20:
                # Calculate how much to offset
                offset = text_surf.get_width() - (input_width - 20)
                # Create a subsurface showing only the visible portion
                visible_width = min(text_surf.get_width(), input_width - 20)
                text_x = input_x + 10
                text_y = input_y + input_height / 2 - text_surf.get_height() / 2
                
                # Clip the text
                clip_rect = pygame.Rect(offset, 0, visible_width, text_surf.get_height())
                clipped_surf = text_surf.subsurface(clip_rect)
                self.screen.blit(clipped_surf, (text_x, text_y))
            else:
                text_x = input_x + 10
                text_y = input_y + input_height / 2 - text_surf.get_height() / 2
                self.screen.blit(text_surf, (text_x, text_y))
        else:
            # Placeholder text
            placeholder_text = "Search for a song..." if not self.search_results else "Search for a song..."
            placeholder_surf = self.instructions_font.render(placeholder_text, True, (100, 100, 120))
            text_x = input_x + 10
            text_y = input_y + input_height / 2 - placeholder_surf.get_height() / 2
            self.screen.blit(placeholder_surf, (text_x, text_y))
        
        # Blinking cursor
        if int(self.frame_count / 30) % 2 == 0:
            if self.url_input_text:
                cursor_text_surf = self.instructions_font.render(self.url_input_text, True, (255, 255, 255))
                cursor_x = input_x + 10 + min(cursor_text_surf.get_width(), input_width - 20)
            else:
                cursor_x = input_x + 10
            cursor_y = input_y + 10
            pygame.draw.line(self.screen, (255, 255, 255), 
                           (cursor_x, cursor_y), (cursor_x, cursor_y + 40), 2)
        
        # Show search results if available
        if self.search_results:
            results_area_top = 220
            results_area_bottom = WINDOW_HEIGHT - 120
            result_height = 80
            result_spacing = 10
            
            # Instructions for results
            instruction_surf = self.instructions_font.render("Click a video to select:", True, (200, 200, 220))
            self.screen.blit(instruction_surf, (center_x - instruction_surf.get_width() / 2, 190))
            
            # Draw search results
            for i, video in enumerate(self.search_results[:5]):  # Show max 5 results
                result_y = results_area_top + i * (result_height + result_spacing) - self.search_scroll
                
                # Only render if visible
                if result_y + result_height < results_area_top or result_y > results_area_bottom:
                    continue
                
                result_rect = pygame.Rect(70, result_y, WINDOW_WIDTH - 140, result_height)
                
                # Check hover
                mouse_pos = pygame.mouse.get_pos()
                scale, offset_x, offset_y = self._get_scale_and_offset()
                logical_mouse_x = (mouse_pos[0] - offset_x) / scale
                logical_mouse_y = (mouse_pos[1] - offset_y) / scale
                
                is_hover = result_rect.collidepoint(logical_mouse_x, logical_mouse_y)
                is_selected = i == self.selected_video_index
                
                # Background color
                if is_selected:
                    bg_color = (80, 150, 100)
                    border_color = (150, 255, 150)
                elif is_hover:
                    bg_color = (70, 70, 90)
                    border_color = (120, 120, 200)
                else:
                    bg_color = (50, 50, 70)
                    border_color = (90, 90, 110)
                
                pygame.draw.rect(self.screen, bg_color, result_rect, border_radius=8)
                pygame.draw.rect(self.screen, border_color, result_rect, 2, border_radius=8)
                
                # Video title
                title = video['title']
                if len(title) > 50:
                    title = title[:47] + "..."
                title_surf = self.instructions_font.render(title, True, (255, 255, 255))
                self.screen.blit(title_surf, (result_rect.x + 10, result_rect.y + 10))
                
                # Video author and length
                minutes = video['length'] // 60
                seconds = video['length'] % 60
                info = f"{video['author']} • {minutes}:{seconds:02d}"
                if len(info) > 60:
                    info = info[:57] + "..."
                info_font = pygame.font.Font(None, 24)
                info_surf = info_font.render(info, True, (180, 180, 200))
                self.screen.blit(info_surf, (result_rect.x + 10, result_rect.y + 45))
        
        # Loading indicator
        if self.is_searching:
            loading_surf = self.instructions_title_font.render("Searching...", True, (255, 200, 100))
            self.screen.blit(loading_surf, (center_x - loading_surf.get_width() / 2, center_y))
        
        # Buttons
        button_width = 250
        button_height = 70
        button_spacing = 30
        
        # Get mouse position for hover effects
        mouse_pos = pygame.mouse.get_pos()
        scale, offset_x, offset_y = self._get_scale_and_offset()
        logical_mouse_x = (mouse_pos[0] - offset_x) / scale
        logical_mouse_y = (mouse_pos[1] - offset_y) / scale
        
        # Button Y position depends on whether we have search results
        button_y = WINDOW_HEIGHT / 2 + 120 if not self.search_results else WINDOW_HEIGHT - 100
        
        # Search button (changes to "Start Game" if video selected)
        search_rect = pygame.Rect(center_x - button_width - button_spacing / 2, button_y, button_width, button_height)
        search_hover = search_rect.collidepoint(logical_mouse_x, logical_mouse_y)
        
        # Determine button text and state
        if self.selected_video_index >= 0:
            search_text = "Start Game"
            search_enabled = True
        else:
            search_text = "Search"
            search_enabled = len(self.url_input_text.strip()) > 0
        
        if search_enabled:
            search_color = (100, 200, 100) if search_hover else (60, 120, 60)
            search_text_color = (255, 255, 255) if search_hover else (200, 200, 200)
            search_border_color = (150, 255, 150)
        else:
            search_color = (40, 40, 40)
            search_text_color = (100, 100, 100)
            search_border_color = (80, 80, 80)
        
        pygame.draw.rect(self.screen, search_color, search_rect, border_radius=12)
        pygame.draw.rect(self.screen, search_border_color, search_rect, 3, border_radius=12)
        
        self._queue_text(
            self._text_overlays,
            self.button_font,
            search_text,
            search_text_color,
            center_x - button_width / 2 - button_spacing / 2,
            button_y + button_height / 2 - 18,
            center=True,
            font_size=self.button_font_size
        )
        
        # Cancel button
        cancel_rect = pygame.Rect(center_x + button_spacing / 2, button_y, button_width, button_height)
        cancel_hover = cancel_rect.collidepoint(logical_mouse_x, logical_mouse_y)
        cancel_color = (200, 100, 100) if cancel_hover else (120, 60, 60)
        cancel_text_color = (255, 255, 255) if cancel_hover else (200, 200, 200)
        
        pygame.draw.rect(self.screen, cancel_color, cancel_rect, border_radius=12)
        pygame.draw.rect(self.screen, (255, 150, 150), cancel_rect, 3, border_radius=12)
        
        self._queue_text(
            self._text_overlays,
            self.button_font,
            "Cancel",
            cancel_text_color,
            center_x + button_width / 2 + button_spacing / 2,
            button_y + button_height / 2 - 18,
            center=True,
            font_size=self.button_font_size
        )
    
    def _render_loading(self):
        """Render the loading screen with animation."""
        center_x = WINDOW_WIDTH / 2
        center_y = WINDOW_HEIGHT / 2
        
        # Semi-transparent overlay
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(220)
        overlay.fill((10, 10, 20))
        self.screen.blit(overlay, (0, 0))
        
        # Animated loading text
        import math
        dots_count = int(self.frame_count / 20) % 4
        dots = "." * dots_count
        loading_text = f"Loading{dots}"
        
        self._queue_text(
            self._text_overlays,
            self.instructions_title_font,
            loading_text,
            (100, 255, 200),
            center_x,
            center_y - 80,
            center=True,
            font_size=self.instructions_title_font_size
        )
        
        # Loading message
        if self.loading_message:
            self._queue_text(
                self._text_overlays,
                self.instructions_font,
                self.loading_message,
                (200, 200, 220),
                center_x,
                center_y + 20,
                center=True,
                font_size=self.instructions_font_size
            )
        
        # Spinning circle animation
        radius = 50
        segments = 12
        for i in range(segments):
            angle = (self.frame_count * 0.05) + (i * 2 * math.pi / segments)
            x = center_x + math.cos(angle) * radius
            y = center_y - 20 + math.sin(angle) * radius
            
            # Fade effect
            alpha = int(255 * (1 - i / segments))
            size = 8 - int(4 * (i / segments))
            
            circle_surface = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(circle_surface, (100, 200, 255, alpha), (size, size), size)
            self.screen.blit(circle_surface, (x - size, y - size))
    
    def update_loading(self, message):
        """Update the loading screen with a new message."""
        self.loading_message = message
        self.frame_count += 1

        
        # Render
        self._text_overlays = []
        self.screen.blit(self.background, (0, 0))
        self._render_loading()
        scale, offset_x, offset_y = self._present_canvas()
        self._draw_text_overlays(scale, offset_x, offset_y)
        pygame.time.Clock().tick(60)
    
    def update_loading_loop(self, message, is_complete_callback):
        """Keep updating the loading screen animation until the callback returns True."""
        self.loading_message = message
        clock = pygame.time.Clock()
        
        while not is_complete_callback():
            self.frame_count += 1
            
            # Handle events to keep window responsive
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    import sys
                    sys.exit(0)
            
            # Render
            self._text_overlays = []
            self.screen.blit(self.background, (0, 0))
            self._render_loading()
            scale, offset_x, offset_y = self._present_canvas()
            self._draw_text_overlays(scale, offset_x, offset_y)
            clock.tick(60)
    
    def _render_main_menu(self):
        """Render the main menu screen."""
        center_x = WINDOW_WIDTH / 2
        
        # Animated title with pulse effect
        import math
        pulse = math.sin(self.frame_count * 0.05) * 0.1 + 1.0
        
        # Title "RhythmGen" with dual-color shadow effect
        title_y = 120
        self._queue_text(
            self._text_overlays,
            self.title_font,
            "RhythmGen",
            (0, 255, 200),
            center_x + 3,
            title_y + 3,
            center=True,
            font_size=self.title_font_size
        )
        self._queue_text(
            self._text_overlays,
            self.title_font,
            "RhythmGen",
            (255, 0, 200),
            center_x,
            title_y,
            center=True,
            font_size=self.title_font_size
        )
        
        # Subtitle
        self._queue_text(
            self._text_overlays,
            self.subtitle_font,
            "AI-Powered Rhythm Game",
            (180, 180, 220),
            center_x,
            title_y + 90,
            center=True,
            font_size=self.subtitle_font_size
        )
        
        # Buttons
        button_width = 300
        button_height = 70
        button_spacing = 30
        
        # Calculate starting Y position for centered buttons
        total_height = (button_height * 3) + (button_spacing * 2)
        start_y = (WINDOW_HEIGHT / 2) - (total_height / 2) + 80
        
        # Get mouse position for hover effects
        mouse_pos = pygame.mouse.get_pos()
        scale, offset_x, offset_y = self._get_scale_and_offset()
        logical_mouse_x = (mouse_pos[0] - offset_x) / scale
        logical_mouse_y = (mouse_pos[1] - offset_y) / scale
        
        # Play button
        play_rect = pygame.Rect(center_x - button_width / 2, start_y, button_width, button_height)
        play_hover = play_rect.collidepoint(logical_mouse_x, logical_mouse_y)
        play_color = (100, 200, 100) if play_hover else (60, 120, 60)
        play_text_color = (255, 255, 255) if play_hover else (200, 200, 200)
        
        pygame.draw.rect(self.screen, play_color, play_rect, border_radius=12)
        pygame.draw.rect(self.screen, (150, 255, 150), play_rect, 3, border_radius=12)
        
        self._queue_text(
            self._text_overlays,
            self.button_font,
            "Play",
            play_text_color,
            center_x,
            start_y + button_height / 2 - 18,
            center=True,
            font_size=self.button_font_size
        )
        
        # How To Play button
        howto_y = start_y + button_height + button_spacing
        howto_rect = pygame.Rect(center_x - button_width / 2, howto_y, button_width, button_height)
        howto_hover = howto_rect.collidepoint(logical_mouse_x, logical_mouse_y)
        howto_color = (100, 100, 200) if howto_hover else (60, 60, 120)
        howto_text_color = (255, 255, 255) if howto_hover else (200, 200, 200)
        
        pygame.draw.rect(self.screen, howto_color, howto_rect, border_radius=12)
        pygame.draw.rect(self.screen, (150, 150, 255), howto_rect, 3, border_radius=12)
        
        self._queue_text(
            self._text_overlays,
            self.button_font,
            "How To Play",
            howto_text_color,
            center_x,
            howto_y + button_height / 2 - 18,
            center=True,
            font_size=self.button_font_size
        )
        
        # Quit button
        quit_y = start_y + (button_height + button_spacing) * 2
        quit_rect = pygame.Rect(center_x - button_width / 2, quit_y, button_width, button_height)
        quit_hover = quit_rect.collidepoint(logical_mouse_x, logical_mouse_y)
        quit_color = (200, 100, 100) if quit_hover else (120, 60, 60)
        quit_text_color = (255, 255, 255) if quit_hover else (200, 200, 200)
        
        pygame.draw.rect(self.screen, quit_color, quit_rect, border_radius=12)
        pygame.draw.rect(self.screen, (255, 150, 150), quit_rect, 3, border_radius=12)
        
        self._queue_text(
            self._text_overlays,
            self.button_font,
            "Quit",
            quit_text_color,
            center_x,
            quit_y + button_height / 2 - 18,
            center=True,
            font_size=self.button_font_size
        )
    
    def run(self):
        """Run the main menu and return the user's choice."""
        # Ensure pygame is initialized (in case returning from game)
        if not pygame.get_init():
            pygame.init()
        
        # Ensure display is initialized
        if not pygame.display.get_surface():
            try:
                self.display_surface = pygame.display.set_mode(self.display_size, pygame.FULLSCREEN)
            except pygame.error:
                self.display_surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
                self.display_size = (WINDOW_WIDTH, WINDOW_HEIGHT)
        
        clock = pygame.time.Clock()
        running = True
        choice = None
        
        while running:
            self.frame_count += 1
            
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    choice = "quit"
                    running = False
                
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.showing_instructions:
                            self.showing_instructions = False
                            self.instructions_scroll = 0  # Reset scroll
                        elif self.showing_url_input:
                            self.showing_url_input = False
                            self.url_input_text = ""  # Clear input
                        else:
                            choice = "quit"
                            running = False
                    
                    # Handle text input on URL screen
                    elif self.showing_url_input:
                        if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                            # Search or start game based on state
                            if self.selected_video_index >= 0:
                                # Start game with selected video
                                selected_video = self.search_results[self.selected_video_index]
                                video_url = f"https://youtube.com/watch?v={selected_video['watch_url']}"
                                choice = ("play", video_url)
                                # Show loading screen and exit loop
                                self.showing_url_input = False
                                self.showing_loading = True
                                self.loading_message = "Preparing..."
                                running = False
                            elif self.url_input_text.strip():
                                # Perform search
                                self.is_searching = True
                                    # Search will be triggered after this event loop
                        elif event.key == pygame.K_BACKSPACE:
                            self.url_input_text = self.url_input_text[:-1]
                            # Clear search results if input changes
                            if self.search_results:
                                self.search_results = []
                                self.selected_video_index = -1
                                self.search_scroll = 0
                        elif event.key == pygame.K_v and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                            # Paste from clipboard
                            try:
                                import pygame.scrap as pg_scrap
                                pg_scrap.init()
                                clipboard_data = pg_scrap.get(pygame.SCRAP_TEXT)
                                if clipboard_data:
                                    pasted_text = clipboard_data.decode('utf-8').strip()
                                    self.url_input_text += pasted_text
                                    # Clear search results if input changes
                                    if self.search_results:
                                        self.search_results = []
                                        self.selected_video_index = -1
                                        self.search_scroll = 0
                            except:
                                pass  # Clipboard not available
                        elif event.key == pygame.K_UP and self.search_results:
                            # Navigate up in search results
                            if self.selected_video_index > 0:
                                self.selected_video_index -= 1
                        elif event.key == pygame.K_DOWN and self.search_results:
                            # Navigate down in search results
                            if self.selected_video_index < len(self.search_results) - 1:
                                self.selected_video_index += 1
                        else:
                            # Add character to input
                            if event.unicode and len(self.url_input_text) < 200:  # Max 200 chars
                                self.url_input_text += event.unicode
                                # Clear search results if input changes
                                if self.search_results:
                                    self.search_results = []
                                    self.selected_video_index = -1
                                    self.search_scroll = 0
                    
                    # Scroll with arrow keys in instructions
                    elif self.showing_instructions:
                        if event.key == pygame.K_UP or event.key == pygame.K_w:
                            self.instructions_scroll -= 40
                        elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                            self.instructions_scroll += 40
                        elif event.key == pygame.K_PAGEUP:
                            self.instructions_scroll -= 200
                        elif event.key == pygame.K_PAGEDOWN:
                            self.instructions_scroll += 200
                        elif event.key == pygame.K_HOME:
                            self.instructions_scroll = 0
                        elif event.key == pygame.K_END:
                            self.instructions_scroll = self.max_instructions_scroll
                
                # Mouse wheel scrolling in instructions
                if event.type == pygame.MOUSEWHEEL and self.showing_instructions:
                    self.instructions_scroll -= event.y * 40  # Negative because wheel up = positive y
                
                # Mouse wheel scrolling in search results
                if event.type == pygame.MOUSEWHEEL and self.showing_url_input and self.search_results:
                    self.search_scroll -= event.y * 40
                    self.search_scroll = max(0, self.search_scroll)
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_x, mouse_y = event.pos
                    # Adjust for scaling
                    scale, offset_x, offset_y = self._get_scale_and_offset()
                    logical_x = (mouse_x - offset_x) / scale
                    logical_y = (mouse_y - offset_y) / scale
                    
                    action = self._check_button_click(logical_x, logical_y)
                    if action:
                        if action == "howto":
                            self.showing_instructions = True
                            self.instructions_scroll = 0  # Reset scroll when opening
                        elif action == "back":
                            self.showing_instructions = False
                            self.instructions_scroll = 0  # Reset scroll when closing
                        elif action == "play":
                            self.showing_url_input = True
                            self.url_input_text = ""  # Clear any previous input
                            self.search_results = []
                            self.selected_video_index = -1
                            self.search_scroll = 0
                        elif action == "search":
                            if self.selected_video_index >= 0:
                                # Start game with selected video
                                selected_video = self.search_results[self.selected_video_index]
                                video_url = f"https://youtube.com/watch?v={selected_video['watch_url']}"
                                choice = ("play", video_url)
                                # Show loading screen and exit loop
                                self.showing_url_input = False
                                self.showing_loading = True
                                self.loading_message = "Preparing..."
                                running = False
                            elif self.url_input_text.strip():
                                # Perform search
                                self.is_searching = True
                        elif action == "cancel":
                            self.showing_url_input = False
                            self.url_input_text = ""
                            self.search_results = []
                            self.selected_video_index = -1
                            self.search_scroll = 0
                        elif isinstance(action, tuple) and action[0] == "select_video":
                            # Video selected from search results
                            self.selected_video_index = action[1]
                        else:
                            choice = action
                            running = False
            
            # Perform search if flagged (do this outside event loop to avoid blocking)
            if self.is_searching and self.showing_url_input:
                # Only start a new search if one isn't already running
                if self.search_thread is None or not self.search_thread.is_alive():
                    search_query = self.url_input_text
                    
                    def search_task():
                        try:
                            print(f"Searching for: {search_query}")
                            results = suggest_youtube_videos(search_query)
                            # Update results safely (this will be read by main thread)
                            self.search_results = results
                            if results:
                                self.selected_video_index = 0  # Auto-select first result
                            print(f"Found {len(results)} results")
                        except Exception as e:
                            print(f"Search error: {e}")
                            self.search_results = []
                            self.selected_video_index = -1
                        finally:
                            self.is_searching = False
                    
                    # Start search in background thread
                    self.search_thread = threading.Thread(target=search_task, daemon=True)
                    self.search_thread.start()
            
            # Render
            self._text_overlays = []
            self.screen.blit(self.background, (0, 0))
            
            if self.showing_loading:
                self._render_loading()
            elif self.showing_instructions:
                self._render_instructions()
            elif self.showing_url_input:
                self._render_url_input()
            else:
                self._render_main_menu()
            
            scale, offset_x, offset_y = self._present_canvas()
            self._draw_text_overlays(scale, offset_x, offset_y)
            
            clock.tick(60)
        
        return choice

