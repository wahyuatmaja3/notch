import asyncio
import threading
import time
from PyQt6.QtCore import QObject, pyqtSignal

try:
    import winsdk.windows.ui.notifications.management as unm
    import winsdk.windows.ui.notifications as uin
    HAS_WIN_NOTIF = True
except Exception:
    HAS_WIN_NOTIF = False


class NotificationService(QObject):
    # Emits dict with keys: id, app_name, title, message, time_str, timestamp
    notification_received = pyqtSignal(dict)
    notifications_cleared = pyqtSignal()

    def __init__(self, config=None):
        super().__init__()
        self.config = config
        self.history = []
        self._listener = None
        self._loop = None
        self._thread = None
        self._next_id = 1

    def start(self):
        """Start listening for Windows toast notifications in background thread."""
        if not HAS_WIN_NOTIF:
            print("[NotificationService] WinRT Notification listener not available.")
            return

        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        asyncio.run_coroutine_threadsafe(self._init_listener(), self._loop)

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    async def _init_listener(self):
        try:
            self._listener = unm.UserNotificationListener.get_current()
            access_status = await self._listener.request_access_async()
            if access_status == unm.UserNotificationListenerAccessStatus.ALLOWED:
                print("[NotificationService] Windows Notification Listener access granted!")
                self._listener.add_notification_changed(self._on_notification_changed)
            else:
                print(f"[NotificationService] Notification access status: {access_status}")
        except Exception as e:
            print(f"[NotificationService] Init error: {e}")

    def _on_notification_changed(self, sender, args):
        try:
            notif_id = args.user_notification_id
            if args.change_kind == unm.UserNotificationUpdateKind.ADDED:
                n = self._listener.get_notification(notif_id)
                if n and n.notification and n.notification.visual:
                    app_name = "Windows"
                    if n.app_info and n.app_info.display_info:
                        app_name = n.app_info.display_info.display_name or "App"
                    
                    binding = n.notification.visual.get_binding("ToastGeneric")
                    elements = binding.get_text_elements() if binding else []
                    title = elements[0].text if len(elements) > 0 else app_name
                    message = elements[1].text if len(elements) > 1 else ""

                    filter_list = self.config.get("notification_filter", []) if self.config else []
                    # Check if app is in filter or filter is empty/allowed
                    app_lower = app_name.lower()
                    if not filter_list or any(f in app_lower for f in filter_list) or "all" in filter_list:
                        self.post_notification(app_name, title, message)
        except Exception as e:
            print(f"[NotificationService] Notification change error: {e}")

    def post_notification(self, app_name: str, title: str, message: str) -> dict:
        notif = {
            "id": self._next_id,
            "app_name": app_name,
            "title": title,
            "message": message,
            "time_str": time.strftime("%H:%M"),
            "timestamp": time.time()
        }
        self._next_id += 1
        self.history.insert(0, notif)
        if len(self.history) > 30:
            self.history = self.history[:30]
        self.notification_received.emit(notif)
        return notif

    def clear_history(self):
        self.history.clear()
        self.notifications_cleared.emit()
