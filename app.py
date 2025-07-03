# app.py - Textual TUI for dev-container management
from typing import Optional
from textual.app import App, ComposeResult
from textual.widgets import DataTable, Footer, Header, Input
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
import logging

import devctl
from config import CONTAINER_PREFIX, IMAGE_TAG
from utils import validate_container_name, logger

class ContainerCreateScreen(Screen):
    """Screen for creating a new container."""
    
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Input(placeholder="Container name", id="name_input")
            yield Input(placeholder=f"Image (default: {IMAGE_TAG})", id="image_input")
        yield Footer()
    
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        if event.input.id == "name_input":
            # Move to image input
            self.query_one("#image_input").focus()
        elif event.input.id == "image_input":
            # Create container
            name = self.query_one("#name_input").value
            image = self.query_one("#image_input").value or IMAGE_TAG
            
            if name:
                self.dismiss((name, image))


class DevBoxUI(App):
    """Terminal UI for managing dev containers."""
    
    CSS_PATH = None  # inline styling not needed
    BINDINGS = [
        Binding("c", "create", "Create Container"),
        Binding("d", "delete", "Delete Container"),
        Binding("s", "stop", "Stop Container"),
        Binding("S", "start", "Start Container"),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]
    
    def __init__(self):
        super().__init__()
        self.highlighted_container: Optional[str] = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="tbl")
        yield Footer()

    async def on_mount(self):
        """Called when app starts."""
        await self.refresh_table()

    async def refresh_table(self):
        """Refresh the container list."""
        try:
            tbl: DataTable = self.query_one("#tbl")
            tbl.clear(columns=True)
            tbl.add_columns("Name", "Status", "Port", "Image")
            
            containers = devctl.list_all()
            if not containers:
                self.notify("No containers found. Press 'c' to create one.", severity="information")
                return
            
            for c in containers:
                # Extract port safely
                port = "N/A"
                if "22/tcp" in c.ports and c.ports["22/tcp"]:
                    port = c.ports["22/tcp"][0]["HostPort"]
                
                # Remove prefix for display
                display_name = c.name.replace(CONTAINER_PREFIX, "")
                
                # Get image name
                image = c.image.tags[0] if c.image.tags else c.image.short_id
                
                tbl.add_row(
                    display_name,
                    c.status,
                    port,
                    image,
                    key=display_name  # Use clean name as key
                )
            
            tbl.focus()
        except Exception as e:
            logger.error(f"Failed to refresh table: {e}")
            self.notify(f"Error refreshing containers: {e}", severity="error")

    async def on_data_table_row_highlighted(self, event):
        """Track highlighted container."""
        if event.row_key:
            self.highlighted_container = str(event.row_key.value)

    async def on_data_table_row_selected(self, event):
        """Open selected container in Cursor."""
        if event.row_key:
            name = str(event.row_key.value)
            try:
                devctl.open_cursor(name)
                self.notify(f"Opening {name} in Cursor...", severity="information")
            except ValueError as e:
                self.notify(str(e), severity="error")
            except Exception as e:
                logger.error(f"Failed to open container: {e}")
                self.notify(f"Error opening container: {e}", severity="error")

    async def action_create(self):
        """Create a new container."""
        def check_create(result):
            if result:
                name, image = result
                try:
                    # Validate name
                    validate_container_name(name)
                    
                    # Create container
                    container, port = devctl.create(name, image=image)
                    self.notify(f"Created {name} on port {port}", severity="success")
                    self.call_after_refresh(self.refresh_table)
                except ValueError as e:
                    self.notify(str(e), severity="error")
                except Exception as e:
                    logger.error(f"Failed to create container: {e}")
                    self.notify(f"Error creating container: {e}", severity="error")
        
        await self.push_screen(ContainerCreateScreen(), check_create)

    async def action_delete(self):
        """Delete the highlighted container."""
        if not self.highlighted_container:
            self.notify("No container selected", severity="warning")
            return
        
        # Confirm deletion
        confirmed = await self.confirm(f"Delete container '{self.highlighted_container}'?")
        if confirmed:
            try:
                devctl.remove_container(self.highlighted_container, force=True)
                self.notify(f"Deleted {self.highlighted_container}", severity="success")
                await self.refresh_table()
            except ValueError as e:
                self.notify(str(e), severity="error")
            except Exception as e:
                logger.error(f"Failed to delete container: {e}")
                self.notify(f"Error deleting container: {e}", severity="error")

    async def action_stop(self):
        """Stop the highlighted container."""
        if not self.highlighted_container:
            self.notify("No container selected", severity="warning")
            return
        
        try:
            devctl.stop_container(self.highlighted_container)
            self.notify(f"Stopped {self.highlighted_container}", severity="success")
            await self.refresh_table()
        except ValueError as e:
            self.notify(str(e), severity="error")
        except Exception as e:
            logger.error(f"Failed to stop container: {e}")
            self.notify(f"Error stopping container: {e}", severity="error")

    async def action_start(self):
        """Start the highlighted container."""
        if not self.highlighted_container:
            self.notify("No container selected", severity="warning")
            return
        
        try:
            devctl.start_container(self.highlighted_container)
            self.notify(f"Started {self.highlighted_container}", severity="success")
            await self.refresh_table()
        except ValueError as e:
            self.notify(str(e), severity="error")
        except Exception as e:
            logger.error(f"Failed to start container: {e}")
            self.notify(f"Error starting container: {e}", severity="error")

    async def action_refresh(self):
        """Refresh the container list."""
        await self.refresh_table()
        self.notify("Refreshed container list", severity="information")

    async def confirm(self, message: str) -> bool:
        """Show a confirmation dialog."""
        # For now, we'll auto-confirm. In production, implement a proper dialog
        return True


if __name__ == "__main__":
    try:
        app = DevBoxUI()
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"Error: {e}")