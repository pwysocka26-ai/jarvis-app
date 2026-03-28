import { Tabs } from 'expo-router';

export default function TabsLayout() {
  return (
    <Tabs screenOptions={{ headerShown: false }}>
      <Tabs.Screen name="index" options={{ title: 'Home' }} />
      <Tabs.Screen name="tomorrow" options={{ title: 'Kalendarz' }} />
      <Tabs.Screen name="inbox" options={{ title: 'Projekty' }} />
      <Tabs.Screen name="brain" options={{ title: 'Czat' }} />
      <Tabs.Screen name="settings" options={{ title: 'Ustawienia' }} />
    </Tabs>
  );
}
