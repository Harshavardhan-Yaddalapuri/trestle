export type AlertFrequency = "immediate" | "daily" | "weekly";

export interface NotificationPreferences {
  emailAlerts: boolean;
  inAppAlerts: boolean;
  weeklyDigest: boolean;
  alertFrequency: AlertFrequency;
}

export interface UserSettings {
  schemaVersion: 1;
  notifications: NotificationPreferences;
}
