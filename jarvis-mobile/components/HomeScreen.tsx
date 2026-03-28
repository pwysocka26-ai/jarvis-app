import React, { useMemo } from 'react';
import { Image, ScrollView, Text, View } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { MaterialCommunityIcons } from '@expo/vector-icons';

type HomeCard = {
  key: 'today' | 'todo' | 'week' | 'inbox' | string;
  title: string;
  value: string;
  subtitle: string;
};

type Props = {
  homeCards: readonly HomeCard[];
  today: Date;
};

const palette = {
  text: '#33456C',
  muted: '#8E97B6',
  border: '#E5E8FB',
};

function buildWeek(date: Date) {
  const mondayOffset = (date.getDay() + 6) % 7;
  const monday = new Date(date);
  monday.setDate(date.getDate() - mondayOffset);
  return Array.from({ length: 7 }).map((_, index) => {
    const current = new Date(monday);
    current.setDate(monday.getDate() + index);
    return current;
  });
}

const cardMeta = {
  today: {
    icon: 'check-circle-outline' as const,
    iconColor: '#F2A35E',
    iconBg: '#FFE9D7',
    gradient: ['#FBF1EB', '#F7ECE6'] as const,
    miniIcon: 'clock-outline' as const,
    miniColor: '#E3B7BE',
  },
  todo: {
    icon: 'calendar-month-outline' as const,
    iconColor: '#738CFF',
    iconBg: '#E7EAFF',
    gradient: ['#F1EDFF', '#ECE8FF'] as const,
    miniIcon: 'badge-account-horizontal-outline' as const,
    miniColor: '#9BA7FF',
  },
  week: {
    icon: 'calendar-week' as const,
    iconColor: '#74C7E6',
    iconBg: '#E2F4FA',
    gradient: ['#EDF7F8', '#E8F4F5'] as const,
    miniIcon: 'send-outline' as const,
    miniColor: '#8ECFE3',
  },
  inbox: {
    icon: 'package-variant-closed' as const,
    iconColor: '#8A94FF',
    iconBg: '#ECE7FF',
    gradient: ['#F3EEFF', '#EFEAFF'] as const,
    miniIcon: 'send-outline' as const,
    miniColor: '#A7AEFF',
  },
} as const;

const quickActions = [
  {
    icon: 'plus',
    title: 'Nowe\nzadanie',
    gradient: ['#FBEAF2', '#F6EAF8'] as const,
    iconBg: '#F8DDEA',
    iconColor: '#D86A94',
  },
  {
    icon: 'cart-outline',
    title: 'Lista\nzakupów',
    gradient: ['#EAF9F4', '#E7FAFD'] as const,
    iconBg: '#DFF7F1',
    iconColor: '#58BAC4',
  },
  {
    icon: 'lightbulb-on-outline',
    title: 'Pomysły',
    gradient: ['#EDF2FF', '#EDF3FF'] as const,
    iconBg: '#DFE9FF',
    iconColor: '#7BA0FF',
  },
  {
    icon: 'map-marker-outline',
    title: 'Wyślij\nadres Ani',
    gradient: ['#FDF0E1', '#FDEBDD'] as const,
    iconBg: '#F8E1CA',
    iconColor: '#E2A15B',
  },
] as const;

export default function HomeScreen({ homeCards, today }: Props) {
  const week = useMemo(() => buildWeek(today), [today]);

  return (
    <ScrollView
      contentContainerStyle={{ paddingHorizontal: 14, paddingTop: 10, paddingBottom: 120 }}
      showsVerticalScrollIndicator={false}
    >
      <LinearGradient
        colors={['#F0EEFF', '#ECE9FF']}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={{
          borderRadius: 24,
          borderWidth: 1,
          borderColor: '#E4E7FB',
          overflow: 'hidden',
          minHeight: 110,
          marginBottom: 12,
        }}
      >
        <View style={{ flexDirection: 'row', alignItems: 'flex-end', minHeight: 110 }}>
          <Image
            source={require('../assets/robot.png')}
            style={{
              width: 124,
              height: 108,
              resizeMode: 'contain',
              marginLeft: 4,
              marginBottom: -6,
              marginRight: 6,
            }}
          />
          <Text
            style={{
              flex: 1,
              fontSize: 20,
              lineHeight: 27,
              fontWeight: '400',
              color: palette.text,
              marginBottom: 22,
            }}
          >
            Witaj Mateusz,
          </Text>
        </View>
      </LinearGradient>

      <View style={{ flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', marginBottom: 10 }}>
        {homeCards.map((item) => {
          const meta = cardMeta[(item.key as keyof typeof cardMeta) || 'today'] || cardMeta.today;
          return (
            <LinearGradient
              key={item.key}
              colors={meta.gradient}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 1 }}
              style={{
                width: '48.2%',
                borderRadius: 20,
                borderWidth: 1,
                borderColor: '#E5E8FB',
                paddingHorizontal: 14,
                paddingVertical: 12,
                marginBottom: 10,
              }}
            >
              <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8 }}>
                <View
                  style={{
                    width: 22,
                    height: 22,
                    borderRadius: 8,
                    backgroundColor: meta.iconBg,
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <MaterialCommunityIcons name={meta.icon} size={14} color={meta.iconColor} />
                </View>
                <Text style={{ fontSize: 14, color: palette.text, marginLeft: 8 }}>{item.title}</Text>
              </View>

              <View style={{ height: 1, backgroundColor: 'rgba(194,199,224,0.28)', marginBottom: 9 }} />

              <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 1 }}>
                <MaterialCommunityIcons name={meta.miniIcon} size={15} color={meta.miniColor} style={{ marginRight: 7 }} />
                <Text style={{ fontSize: 22, color: '#2D3E67' }}>{item.value}</Text>
              </View>

              <Text style={{ fontSize: 12, color: palette.muted }}>{item.subtitle}</Text>
            </LinearGradient>
          );
        })}
      </View>

      <LinearGradient
        colors={['#F2EFFF', '#EEE9FF']}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={{
          borderRadius: 22,
          borderWidth: 1,
          borderColor: '#E5E8FB',
          padding: 12,
        }}
      >
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <View style={{ flexDirection: 'row', alignItems: 'center' }}>
            <View style={{ width: 22, height: 22, borderRadius: 8, backgroundColor: '#E7E9FF', alignItems: 'center', justifyContent: 'center' }}>
              <MaterialCommunityIcons name="calendar-month-outline" size={14} color="#7184FF" />
            </View>
            <Text style={{ fontSize: 15, color: palette.text, marginLeft: 8 }}>Kalendarz</Text>
          </View>
          <Text style={{ fontSize: 12, color: '#A4ABD0', fontWeight: '500' }}>v9.7.5 ›</Text>
        </View>

        <View
          style={{
            backgroundColor: 'rgba(255,255,255,0.74)',
            borderRadius: 18,
            borderWidth: 1,
            borderColor: '#E8EBFB',
            paddingHorizontal: 12,
            paddingVertical: 10,
            marginBottom: 10,
          }}
        >
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 }}>
            {['Pn', 'Wt', 'Wto', 'Ws', 'Pt', 'Sob', 'Nd'].map((label) => (
              <Text key={label} style={{ flex: 1, textAlign: 'center', fontSize: 12, color: '#9DA5C6' }}>
                {label}
              </Text>
            ))}
          </View>

          <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 }}>
            {week.map((date, index) => {
              const active = index === 4;
              return (
                <View key={`${date.toISOString()}-${index}`} style={{ flex: 1, alignItems: 'center' }}>
                  <Text
                    style={{
                      minWidth: 30,
                      textAlign: 'center',
                      paddingVertical: 6,
                      borderRadius: 14,
                      overflow: 'hidden',
                      fontSize: 14,
                      color: active ? '#2E4066' : '#A0A8C8',
                      backgroundColor: active ? '#E8E9FF' : 'transparent',
                      fontWeight: active ? '600' : '400',
                    }}
                  >
                    {date.getDate()}
                  </Text>
                </View>
              );
            })}
          </View>

          <View style={{ flexDirection: 'row', justifyContent: 'space-between', paddingHorizontal: 10 }}>
            {['#F49379', '#6F86FF', '#E8B36A', '#9CCDAA', '#71CBEE', '#AA98FF', '#EAB673'].map((color, index) => (
              <View key={index} style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: color }} />
            ))}
          </View>
        </View>

        <View
          style={{
            backgroundColor: 'rgba(247,244,255,0.9)',
            borderRadius: 18,
            borderWidth: 1,
            borderColor: '#E6E9FB',
            padding: 12,
            marginBottom: 10,
          }}
        >
          <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8 }}>
            <View style={{ width: 22, height: 22, borderRadius: 8, backgroundColor: '#E8E9FF', alignItems: 'center', justifyContent: 'center' }}>
              <MaterialCommunityIcons name="cog-outline" size={14} color="#7184FF" />
            </View>
            <Text style={{ fontSize: 15, color: palette.text, marginLeft: 8 }}>Nadchodzące</Text>
          </View>

          <View
            style={{
              backgroundColor: 'rgba(255,255,255,0.78)',
              borderRadius: 14,
              borderWidth: 1,
              borderColor: '#E6E9FB',
              paddingHorizontal: 12,
              paddingVertical: 11,
              flexDirection: 'row',
              alignItems: 'center',
            }}
          >
            <MaterialCommunityIcons name="clock-outline" size={15} color="#B2B8D3" />
            <Text style={{ color: '#5D6888', fontSize: 12, marginLeft: 8 }}>11:00</Text>
            <Text style={{ color: '#5D6888', fontSize: 12, marginLeft: 12, flex: 1 }}>
              Umówione spotkanie z zespołem
            </Text>
          </View>
        </View>

        <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
          {quickActions.map((item) => (
            <LinearGradient
              key={item.title}
              colors={item.gradient}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 1 }}
              style={{
                width: '23.1%',
                borderRadius: 14,
                borderWidth: 1,
                borderColor: '#E5E8FB',
                minHeight: 74,
                paddingHorizontal: 8,
                paddingVertical: 8,
                justifyContent: 'space-between',
              }}
            >
              <View style={{ width: 22, height: 22, borderRadius: 8, backgroundColor: item.iconBg, alignItems: 'center', justifyContent: 'center' }}>
                <MaterialCommunityIcons name={item.icon} size={14} color={item.iconColor} />
              </View>
              <Text style={{ fontSize: 10, lineHeight: 12, color: palette.text }}>{item.title}</Text>
            </LinearGradient>
          ))}
        </View>
      </LinearGradient>
    </ScrollView>
  );
}
