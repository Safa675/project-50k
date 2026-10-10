export const NOTIFICATIONS_CHANGED='blackswan:notifications-changed';

export function notifyNotificationsChanged():void{
  window.dispatchEvent(new Event(NOTIFICATIONS_CHANGED));
}
