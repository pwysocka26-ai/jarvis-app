import { useEffect, useMemo, useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  Pressable,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { useRouter } from 'expo-router';
import { getToday, DayPayload, TimelineItem } from '@/src/api/mobile';
import { colors } from '@/src/theme';

type StatCard = {
  label: string;
  value: number;
  tone: 'warm' | 'violet' | 'mint' | 'lavender';
  onPress: () => void;
};

function getUpcomingItems(timeline: TimelineItem[]) {
  return timeline.slice(0, 3);
}

function getTodayCount(data: DayPayload | null) {
  return data?.timeline?.length ?? 0;
}

function getTodoCount(data: DayPayload | null) {
  return data?.priorities?.filter((item) => item.kind === 'task').length ?? 0;
}

function getWeekCount(data: DayPayload | null) {
  const priorities = data?.priorities ?? [];
  const timeline = data?.timeline ?? [];
  return priorities.length > 0 ? priorities.length : timeline.length;
}

function getProjectsCount(data: DayPayload | null) {
  const uniqueCategories = new Set(
    (data?.priorities ?? [])
      .map((item) => item.category?.trim())
      .filter(Boolean)
  );
  return uniqueCategories.size;
}

function getKindLabel(kind: TimelineItem['kind']) {
  switch (kind) {
    case 'event':
      return 'Spotkanie';
    case 'task':
      return 'Zadanie';
    case 'focus':
      return 'Focus';
    case 'break':
      return 'Przerwa';
    case 'lunch':
      return 'Lunch';
    default:
      return 'Pozycja';
  }
}

function getKindTone(kind: TimelineItem['kind']) {
  switch (kind) {
    case 'event':
      return styles.badgeEvent;
    case 'task':
      return styles.badgeTask;
    case 'focus':
      return styles.badgeFocus;
    case 'break':
      return styles.badgeBreak;
    case 'lunch':
      return styles.badgeLunch;
    default:
      return styles.badgeDefault;
  }
}

export default function HomeScreen() {
  const router = useRouter();
  const [data, setData] = useState<DayPayload | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      setData(await getToday());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const stats = useMemo<StatCard[]>(
    () => [
      {
        label: 'Dzisiaj',
        value: getTodayCount(data),
        tone: 'warm',
        onPress: () => router.push('/(tabs)'),
      },
      {
        label: 'Do zrobienia',
        value: getTodoCount(data),
        tone: 'violet',
        onPress: () => router.push('/(tabs)/tomorrow'),
      },
      {
        label: 'Ten tydzień',
        value: getWeekCount(data),
        tone: 'mint',
        onPress: () => router.push('/(tabs)/brain'),
      },
      {
        label: 'Projekty',
        value: getProjectsCount(data),
        tone: 'lavender',
        onPress: () => router.push('/(tabs)/brain'),
      },
    ],
    [data, router]
  );

  const upcoming = useMemo(() => getUpcomingItems(data?.timeline ?? []), [data]);

  return (
    <View style={styles.screen}>
      <ScrollView
        style={styles.wrap}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.topBar}>
          <View>
            <Text style={styles.h1}>Home</Text>
            <Text style={styles.version}>Wersja 9.7.5</Text>
          </View>

          <View style={styles.topRight}>
            <View style={styles.notificationWrap}>
              <Text style={styles.notificationIcon}>🔔</Text>
              <View style={styles.notificationBadge}>
                <Text style={styles.notificationBadgeText}>3</Text>
              </View>
            </View>

            <View style={styles.avatar}>
              <Text style={styles.avatarText}>M</Text>
            </View>
          </View>
        </View>

        <View style={styles.hero}>
          <View style={styles.robotWrap}>
            <Text style={styles.robotEmoji}>🤖</Text>
          </View>

          <View style={styles.heroTextWrap}>
            <Text style={styles.heroTitle}>Witaj Mateusz! 👋</Text>
            <Text style={styles.heroSubtitle}>
              Masz dziś {getTodayCount(data)} zadań i najbliższy punkt o{' '}
              {data?.summary?.next_time ?? '—'}.
            </Text>

            <Pressable style={styles.refreshButton} onPress={load}>
              <Text style={styles.refreshButtonText}>Odśwież</Text>
            </Pressable>
          </View>
        </View>

        <View style={styles.grid}>
          {stats.map((item) => (
            <Pressable
              key={item.label}
              style={[styles.statCard, styles[item.tone]]}
              onPress={item.onPress}
            >
              <View style={styles.statHeader}>
                <Text style={styles.statLabel}>{item.label}</Text>
                <Text style={styles.chevron}>›</Text>
              </View>

              <Text style={styles.statValue}>{item.value}</Text>
              <Text style={styles.statSub}>zadań</Text>
            </Pressable>
          ))}
        </View>

        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Nadchodzące</Text>
          <Pressable onPress={() => router.push('/(tabs)/tomorrow')}>
            <Text style={styles.sectionLink}>Zobacz wszystko</Text>
          </Pressable>
        </View>

        <View style={styles.upcomingCard}>
          {loading ? (
            <View style={styles.loadingWrap}>
              <ActivityIndicator />
            </View>
          ) : upcoming.length === 0 ? (
            <Text style={styles.emptyText}>Brak nadchodzących pozycji.</Text>
          ) : (
            upcoming.map((item, index) => (
              <View
                key={item.id}
                style={[
                  styles.upcomingRow,
                  index !== upcoming.length - 1 && styles.upcomingRowBorder,
                ]}
              >
                <View style={styles.upcomingLeft}>
                  <View style={styles.timelineDot} />
                  <Text style={styles.upcomingTime}>{item.start}</Text>
                  <Text style={styles.upcomingTitle} numberOfLines={1}>
                    {item.title}
                  </Text>
                </View>

                <View style={[styles.badgeBase, getKindTone(item.kind)]}>
                  <Text style={styles.badgeText}>{getKindLabel(item.kind)}</Text>
                </View>
              </View>
            ))
          )}
        </View>
      </ScrollView>

      <Pressable
        style={styles.fab}
        onPress={() => router.push('/(tabs)/inbox')}
      >
        <Text style={styles.fabText}>＋</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: '#F6F7FB',
  },

  wrap: {
    flex: 1,
    backgroundColor: '#F6F7FB',
  },

  content: {
    padding: 16,
    paddingBottom: 120,
    gap: 16,
  },

  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: 8,
  },

  h1: {
    fontSize: 34,
    fontWeight: '800',
    color: colors.text,
  },

  version: {
    marginTop: 4,
    fontSize: 15,
    color: colors.muted,
    fontWeight: '600',
  },

  topRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },

  notificationWrap: {
    position: 'relative',
    width: 36,
    height: 36,
    alignItems: 'center',
    justifyContent: 'center',
  },

  notificationIcon: {
    fontSize: 22,
  },

  notificationBadge: {
    position: 'absolute',
    top: -2,
    right: -2,
    minWidth: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: '#EC6B8F',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 4,
  },

  notificationBadgeText: {
    color: '#FFFFFF',
    fontSize: 11,
    fontWeight: '800',
  },

  avatar: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: '#E7EAFF',
    borderWidth: 1,
    borderColor: '#D7DBF7',
    alignItems: 'center',
    justifyContent: 'center',
  },

  avatarText: {
    color: colors.text,
    fontWeight: '800',
    fontSize: 18,
  },

  hero: {
    backgroundColor: '#EEF2FF',
    borderRadius: 24,
    padding: 18,
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#E3E8FF',
    gap: 14,
  },

  robotWrap: {
    width: 84,
    height: 84,
    borderRadius: 22,
    backgroundColor: '#F8FAFF',
    alignItems: 'center',
    justifyContent: 'center',
  },

  robotEmoji: {
    fontSize: 42,
  },

  heroTextWrap: {
    flex: 1,
    gap: 6,
  },

  heroTitle: {
    fontSize: 18,
    fontWeight: '800',
    color: colors.text,
  },

  heroSubtitle: {
    fontSize: 14,
    lineHeight: 20,
    color: colors.text,
  },

  refreshButton: {
    alignSelf: 'flex-start',
    marginTop: 4,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 999,
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },

  refreshButtonText: {
    color: colors.text,
    fontWeight: '700',
    fontSize: 13,
  },

  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    gap: 12,
  },

  statCard: {
    width: '48%',
    borderRadius: 24,
    padding: 18,
    minHeight: 136,
    borderWidth: 1,
  },

  warm: {
    backgroundColor: '#FFF3EA',
    borderColor: '#F5E2D3',
  },

  violet: {
    backgroundColor: '#F2EEFF',
    borderColor: '#E3DBFF',
  },

  mint: {
    backgroundColor: '#ECF8F5',
    borderColor: '#D8EEE8',
  },

  lavender: {
    backgroundColor: '#F3F0FF',
    borderColor: '#E5DEFA',
  },

  statHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },

  statLabel: {
    fontSize: 16,
    fontWeight: '700',
    color: colors.text,
  },

  chevron: {
    fontSize: 28,
    lineHeight: 28,
    color: '#8A90A6',
  },

  statValue: {
    marginTop: 22,
    fontSize: 34,
    fontWeight: '800',
    color: colors.text,
  },

  statSub: {
    marginTop: 2,
    fontSize: 14,
    color: colors.muted,
    fontWeight: '500',
  },

  sectionHeader: {
    marginTop: 4,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },

  sectionTitle: {
    fontSize: 18,
    fontWeight: '800',
    color: colors.text,
  },

  sectionLink: {
    color: '#6677FF',
    fontWeight: '700',
    fontSize: 14,
  },

  upcomingCard: {
    backgroundColor: colors.card,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: 14,
    paddingVertical: 8,
    gap: 2,
  },

  loadingWrap: {
    paddingVertical: 24,
  },

  emptyText: {
    paddingVertical: 18,
    color: colors.muted,
  },

  upcomingRow: {
    minHeight: 58,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 10,
  },

  upcomingRowBorder: {
    borderBottomWidth: 1,
    borderBottomColor: '#EEF1F5',
  },

  upcomingLeft: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },

  timelineDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: '#8B88F8',
  },

  upcomingTime: {
    width: 48,
    fontSize: 15,
    fontWeight: '800',
    color: colors.text,
  },

  upcomingTitle: {
    flex: 1,
    fontSize: 15,
    color: colors.text,
    fontWeight: '500',
  },

  badgeBase: {
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },

  badgeEvent: {
    backgroundColor: '#ECEBFF',
  },

  badgeTask: {
    backgroundColor: '#FFF0E1',
  },

  badgeFocus: {
    backgroundColor: '#E8F4FF',
  },

  badgeBreak: {
    backgroundColor: '#EEF7EE',
  },

  badgeLunch: {
    backgroundColor: '#FFF7D8',
  },

  badgeDefault: {
    backgroundColor: '#F3F4F6',
  },

  badgeText: {
    fontSize: 12,
    fontWeight: '700',
    color: colors.text,
  },

  fab: {
    position: 'absolute',
    right: 22,
    bottom: 92,
    width: 62,
    height: 62,
    borderRadius: 31,
    backgroundColor: '#5C7CFA',
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#5C7CFA',
    shadowOpacity: 0.28,
    shadowRadius: 14,
    shadowOffset: { width: 0, height: 8 },
    elevation: 8,
  },

  fabText: {
    color: '#FFFFFF',
    fontSize: 30,
    lineHeight: 30,
    fontWeight: '500',
    marginTop: -2,
  },
});
