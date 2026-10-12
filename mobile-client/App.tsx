
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import {
  apiRequest,
  clearTokens,
  getMe,
  registerCustomer,
  signIn,
} from "./src/api";

type Profile = Awaited<ReturnType<typeof getMe>>;

type Booking = {
  id: number;
  service_type: string;
  booking_date: string;
  booking_time: string;
  address: string;
  status: string;
  quoted_price: string;
};

type RosterItem = {
  id: number;
  service_type: string;
  address: string;
  shift_date: string;
  start_time: string;
  end_time: string;
  status: string;
};

type Summary = {
  today: string;
  bookings_today: number;
  pending_bookings: number;
  confirmed_bookings: number;
  active_employees: number;
};

const SERVICES = [
  "Commercial Cleaning",
  "Office Cleaning",
  "House Cleaning",
  "End of Lease Cleaning",
  "Window Cleaning",
  "Deep Cleaning",
  "Post Construction Cleaning",
];

const GREEN = "#176B4D";
const INK = "#17342B";
const MUTED = "#6B7C74";
const BG = "#F4F7F5";
const BORDER = "#DCE7E0";

function Field(props: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  placeholder?: string;
  secureTextEntry?: boolean;
  keyboardType?: "default" | "email-address" | "phone-pad";
}) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{props.label}</Text>
      <TextInput
        style={styles.input}
        value={props.value}
        onChangeText={props.onChangeText}
        placeholder={props.placeholder || props.label}
        placeholderTextColor="#87968E"
        secureTextEntry={props.secureTextEntry}
        keyboardType={props.keyboardType || "default"}
        autoCapitalize={
          props.keyboardType === "email-address" ? "none" : "sentences"
        }
      />
    </View>
  );
}

function PrimaryButton(props: {
  title: string;
  onPress: () => void;
  disabled?: boolean;
}) {
  return (
    <TouchableOpacity
      accessibilityRole="button"
      style={[styles.primaryButton, props.disabled && { opacity: 0.55 }]}
      onPress={props.onPress}
      disabled={props.disabled}
    >
      <Text style={styles.primaryButtonText}>{props.title}</Text>
    </TouchableOpacity>
  );
}

function SectionTitle(props: { title: string; subtitle?: string }) {
  return (
    <View style={styles.sectionTitle}>
      <Text style={styles.heading}>{props.title}</Text>
      {props.subtitle ? (
        <Text style={styles.muted}>{props.subtitle}</Text>
      ) : null}
    </View>
  );
}

export default function App() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [registerMode, setRegisterMode] = useState(false);

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");

  const [activeTab, setActiveTab] = useState("home");
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [roster, setRoster] = useState<RosterItem[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);

  const [service, setService] = useState(SERVICES[0]);
  const [date, setDate] = useState("");
  const [time, setTime] = useState("09:00");
  const [address, setAddress] = useState("");
  const [suburb, setSuburb] = useState("");
  const [notes, setNotes] = useState("");

  const loadProfile = useCallback(async () => {
    const result = await getMe();
    setProfile(result);
  }, []);

  useEffect(() => {
    loadProfile()
      .catch(() => setProfile(null))
      .finally(() => setLoading(false));
  }, [loadProfile]);

  const loadBookings = async () => {
    const data = await apiRequest<Booking[]>("/bookings/");
    setBookings(data);
  };

  const loadRoster = async () => {
    const data = await apiRequest<RosterItem[]>("/employee/roster/");
    setRoster(data);
  };

  const loadSummary = async () => {
    const data = await apiRequest<Summary>("/company/summary/");
    setSummary(data);
  };

  const runAction = async (action: () => Promise<void>) => {
    setBusy(true);
    setError("");

    try {
      await action();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Something went wrong."
      );
    } finally {
      setBusy(false);
    }
  };

  const handleLogin = async () => {
    await runAction(async () => {
      await signIn(username.trim(), password);
      await loadProfile();
      setActiveTab("home");
    });
  };

  const handleRegister = async () => {
    await runAction(async () => {
      await registerCustomer({
        full_name: fullName.trim(),
        email: username.trim().toLowerCase(),
        phone: phone.trim(),
        password,
      });

      setRegisterMode(false);
      setPassword("");
      Alert.alert(
        "Account created",
        "You can now sign in using your email and password."
      );
    });
  };

  const handleLogout = async () => {
    await clearTokens();
    setProfile(null);
    setBookings([]);
    setRoster([]);
    setSummary(null);
    setPassword("");
    setActiveTab("home");
  };

  const createBooking = async () => {
    await runAction(async () => {
      if (!date.trim() || !address.trim() || !suburb.trim()) {
        throw new Error(
          "Please enter a booking date, property address and suburb/postcode."
        );
      }

      // Date must be YYYY-MM-DD; server validates past dates.
      if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) {
        throw new Error("Enter the date as YYYY-MM-DD.");
      }

      const key =
        `yd-${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;

      await apiRequest<Booking>(
        "/bookings/",
        {
          method: "POST",
          headers: { "Idempotency-Key": key },
          body: JSON.stringify({
            service_type: service,
            booking_date: date,
            booking_time: time,
            address: address.trim(),
            suburb_postcode: suburb.trim(),
            notes: notes.trim(),
          }),
        }
      );

      await loadBookings();
      setActiveTab("bookings");

      Alert.alert(
        "Request submitted",
        "Your booking has been submitted. Check its status in the app."
      );
    });
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.centered}>
        <ActivityIndicator size="large" color={GREEN} />
        <Text style={styles.muted}>Loading YD Commercial Cleaning…</Text>
      </SafeAreaView>
    );
  }

  if (!profile) {
    return (
      <SafeAreaView style={styles.safe}>
        <StatusBar barStyle="dark-content" />
        <ScrollView contentContainerStyle={styles.authContainer}>
          <View style={styles.brandMark}>
            <Text style={styles.brandMarkText}>YD</Text>
          </View>

          <Text style={styles.brandTitle}>YD Commercial Cleaning</Text>
          <Text style={styles.muted}>
            Professional cleaning. Simple management.
          </Text>

          <View style={styles.card}>
            <SectionTitle
              title={registerMode ? "Create your account" : "Welcome back"}
              subtitle={
                registerMode
                  ? "Join YD Commercial Cleaning"
                  : "Sign in to continue"
              }
            />

            {registerMode && (
              <>
                <Field
                  label="Full name"
                  value={fullName}
                  onChangeText={setFullName}
                />
                <Field
                  label="Phone"
                  value={phone}
                  onChangeText={setPhone}
                  keyboardType="phone-pad"
                />
              </>
            )}

            <Field
              label="Email"
              value={username}
              onChangeText={setUsername}
              keyboardType="email-address"
            />
            <Field
              label="Password"
              value={password}
              onChangeText={setPassword}
              secureTextEntry
            />

            {error ? <Text style={styles.error}>{error}</Text> : null}

            <PrimaryButton
              title={
                busy
                  ? "Please wait…"
                  : registerMode
                  ? "Create account"
                  : "Sign in"
              }
              onPress={registerMode ? handleRegister : handleLogin}
              disabled={busy}
            />

            <TouchableOpacity
              style={styles.textButton}
              onPress={() => {
                setError("");
                setRegisterMode(!registerMode);
              }}
            >
              <Text style={styles.linkText}>
                {registerMode
                  ? "Already registered? Sign in"
                  : "New customer? Create an account"}
              </Text>
            </TouchableOpacity>
          </View>

          <Text style={styles.footer}>
            By continuing, use of your account is subject to the company's
            applicable terms and privacy policy.
          </Text>
        </ScrollView>
      </SafeAreaView>
    );
  }

  const isCustomer = profile.roles.includes("customer");
  const isEmployee = profile.roles.includes("employee");
  const isAdmin = profile.roles.includes("company_admin");

  const tabs = [
    { id: "home", label: "Home" },
    ...(isCustomer ? [{ id: "bookings", label: "Bookings" }] : []),
    ...(isCustomer ? [{ id: "new", label: "New booking" }] : []),
    ...(isEmployee ? [{ id: "roster", label: "My work" }] : []),
    ...(isAdmin ? [{ id: "admin", label: "Company" }] : []),
  ];

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="dark-content" />

      <View style={styles.topBar}>
        <View>
          <Text style={styles.brandTitle}>YD Cleaning</Text>
          <Text style={styles.muted}>
            {profile.customer?.full_name ||
              profile.employee?.full_name ||
              profile.user.email}
          </Text>
        </View>

        <TouchableOpacity onPress={handleLogout}>
          <Text style={styles.linkText}>Sign out</Text>
        </TouchableOpacity>
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        {error ? <Text style={styles.error}>{error}</Text> : null}

        {activeTab === "home" && (
          <>
            <View style={styles.hero}>
              <Text style={styles.eyebrow}>YOUR CLEANING PARTNER</Text>
              <Text style={styles.heroTitle}>
                {isAdmin
                  ? "Your business at a glance."
                  : isEmployee
                  ? "Your workday, organised."
                  : "A cleaner space starts here."}
              </Text>
              <Text style={styles.heroBody}>
                {isAdmin
                  ? "Manage company operations from one place."
                  : isEmployee
                  ? "Access your schedule and assigned jobs."
                  : "Manage bookings and cleaning requests in one place."}
              </Text>
            </View>

            {isCustomer && (
              <View style={styles.card}>
                <SectionTitle
                  title="Customer services"
                  subtitle="Book a service or check your requests."
                />
                <PrimaryButton
                  title="Request a cleaning"
                  onPress={() => setActiveTab("new")}
                />
                <View style={styles.spacer} />
                <PrimaryButton
                  title="View my bookings"
                  onPress={() =>
                    runAction(async () => {
                      await loadBookings();
                      setActiveTab("bookings");
                    })
                  }
                />
              </View>
            )}

            {isEmployee && (
              <View style={styles.card}>
                <SectionTitle
                  title="Employee workspace"
                  subtitle="Your assigned roster and shift details."
                />
                <PrimaryButton
                  title="View my work"
                  onPress={() =>
                    runAction(async () => {
                      await loadRoster();
                      setActiveTab("roster");
                    })
                  }
                />
              </View>
            )}

            {isAdmin && (
              <View style={styles.card}>
                <SectionTitle
                  title="Company overview"
                  subtitle="Operational summary from Django."
                />
                <PrimaryButton
                  title="Load company summary"
                  onPress={() =>
                    runAction(async () => {
                      await loadSummary();
                      setActiveTab("admin");
                    })
                  }
                />
              </View>
            )}

            {!isCustomer && !isEmployee && !isAdmin && (
              <View style={styles.card}>
                <SectionTitle
                  title="Account access"
                  subtitle="Your account does not yet have a customer, employee or company role linked."
                />
              </View>
            )}
          </>
        )}

        {activeTab === "new" && isCustomer && (
          <View style={styles.card}>
            <SectionTitle
              title="Request a booking"
              subtitle="Your request will be recorded in the existing Django system."
            />

            <Text style={styles.label}>Cleaning service</Text>
            {SERVICES.map((item) => (
              <TouchableOpacity
                key={item}
                style={[
                  styles.choice,
                  service === item && styles.choiceSelected,
                ]}
                onPress={() => setService(item)}
              >
                <Text
                  style={[
                    styles.choiceText,
                    service === item && styles.choiceTextSelected,
                  ]}
                >
                  {item}
                </Text>
              </TouchableOpacity>
            ))}

            <Field
              label="Date (YYYY-MM-DD)"
              value={date}
              onChangeText={setDate}
              placeholder="2026-11-15"
            />
            <Field
              label="Time (HH:MM)"
              value={time}
              onChangeText={setTime}
              placeholder="09:00"
            />
            <Field
              label="Property address"
              value={address}
              onChangeText={setAddress}
            />
            <Field
              label="Suburb and postcode"
              value={suburb}
              onChangeText={setSuburb}
            />
            <Field
              label="Additional notes (optional)"
              value={notes}
              onChangeText={setNotes}
            />

            <Text style={styles.muted}>
              Submitting a request does not guarantee that the requested
              time is available or that the booking is confirmed.
            </Text>

            <PrimaryButton
              title={busy ? "Submitting…" : "Submit booking request"}
              onPress={createBooking}
              disabled={busy}
            />
          </View>
        )}

        {activeTab === "bookings" && isCustomer && (
          <View style={styles.card}>
            <SectionTitle
              title="My bookings"
              subtitle="Booking records linked to your customer account."
            />

            <PrimaryButton
              title={busy ? "Loading…" : "Refresh bookings"}
              onPress={() => runAction(loadBookings)}
              disabled={busy}
            />

            {bookings.map((booking) => (
              <View key={booking.id} style={styles.listItem}>
                <Text style={styles.itemTitle}>
                  {booking.service_type}
                </Text>
                <Text style={styles.muted}>
                  {booking.booking_date} · {booking.booking_time}
                </Text>
                <Text style={styles.muted}>{booking.address}</Text>
                <Text style={styles.status}>
                  {booking.status.replace("_", " ").toUpperCase()}
                </Text>
              </View>
            ))}

            {bookings.length === 0 && (
              <Text style={styles.muted}>
                Load your bookings to see existing records.
              </Text>
            )}
          </View>
        )}

        {activeTab === "roster" && isEmployee && (
          <View style={styles.card}>
            <SectionTitle
              title="My work"
              subtitle="Only roster entries assigned to your linked employee profile."
            />
            <PrimaryButton
              title={busy ? "Loading…" : "Refresh roster"}
              onPress={() => runAction(loadRoster)}
              disabled={busy}
            />

            {roster.map((item) => (
              <View key={item.id} style={styles.listItem}>
                <Text style={styles.itemTitle}>{item.service_type}</Text>
                <Text style={styles.muted}>
                  {item.shift_date} · {item.start_time}–{item.end_time}
                </Text>
                <Text style={styles.muted}>{item.address}</Text>
                <Text style={styles.status}>
                  {item.status.toUpperCase()}
                </Text>
              </View>
            ))}

            {roster.length === 0 && (
              <Text style={styles.muted}>
                Load your roster to view assigned work.
              </Text>
            )}
          </View>
        )}

        {activeTab === "admin" && isAdmin && (
          <View style={styles.card}>
            <SectionTitle
              title="Company overview"
              subtitle="Live counts from the Django backend."
            />

            <PrimaryButton
              title={busy ? "Loading…" : "Refresh summary"}
              onPress={() => runAction(loadSummary)}
              disabled={busy}
            />

            {summary && (
              <>
                <Metric label="Bookings today" value={summary.bookings_today} />
                <Metric
                  label="Pending bookings"
                  value={summary.pending_bookings}
                />
                <Metric
                  label="Confirmed bookings"
                  value={summary.confirmed_bookings}
                />
                <Metric
                  label="Active employees"
                  value={summary.active_employees}
                />
              </>
            )}

            <Text style={styles.muted}>
              This is the initial summary screen, not a replacement for
              your full company dashboard.
            </Text>
          </View>
        )}
      </ScrollView>

      <View style={styles.tabBar}>
        {tabs.map((tab) => (
          <TouchableOpacity
            key={tab.id}
            style={[
              styles.tab,
              activeTab === tab.id && styles.tabActive,
            ]}
            onPress={() => setActiveTab(tab.id)}
          >
            <Text
              style={[
                styles.tabText,
                activeTab === tab.id && styles.tabTextActive,
              ]}
            >
              {tab.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {busy && (
        <View style={styles.busyOverlay} pointerEvents="none">
          <ActivityIndicator color={GREEN} size="small" />
        </View>
      )}
    </SafeAreaView>
  );
}

function Metric(props: { label: string; value: number }) {
  return (
    <View style={styles.metric}>
      <Text style={styles.metricValue}>{props.value}</Text>
      <Text style={styles.muted}>{props.label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: BG },
  centered: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
    backgroundColor: BG,
  },
  authContainer: { padding: 24, paddingTop: 42 },
  brandMark: {
    width: 62,
    height: 62,
    borderRadius: 20,
    backgroundColor: GREEN,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 18,
  },
  brandMarkText: { color: "#FFFFFF", fontSize: 23, fontWeight: "800" },
  brandTitle: { color: INK, fontSize: 21, fontWeight: "800" },
  muted: { color: MUTED, fontSize: 13, lineHeight: 20, marginTop: 4 },
  card: {
    backgroundColor: "#FFFFFF",
    borderRadius: 22,
    padding: 18,
    marginTop: 20,
    borderWidth: 1,
    borderColor: BORDER,
  },
  sectionTitle: { marginBottom: 14 },
  heading: { color: INK, fontSize: 20, fontWeight: "800" },
  field: { marginBottom: 15 },
  label: {
    color: INK,
    fontSize: 13,
    fontWeight: "700",
    marginBottom: 7,
  },
  input: {
    backgroundColor: "#FBFCFB",
    borderColor: BORDER,
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 13,
    paddingVertical: 12,
    color: INK,
    fontSize: 15,
  },
  primaryButton: {
    backgroundColor: GREEN,
    padding: 15,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
  },
  primaryButtonText: { color: "#FFFFFF", fontWeight: "700", fontSize: 14 },
  textButton: { alignItems: "center", padding: 15 },
  linkText: { color: GREEN, fontWeight: "700", fontSize: 13 },
  error: {
    color: "#A52A2A",
    backgroundColor: "#FFF0F0",
    padding: 12,
    borderRadius: 10,
    marginVertical: 10,
  },
  footer: {
    color: MUTED,
    fontSize: 12,
    lineHeight: 18,
    marginTop: 22,
  },
  topBar: {
    paddingHorizontal: 20,
    paddingVertical: 14,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: "#FFFFFF",
    borderBottomWidth: 1,
    borderColor: BORDER,
  },
  content: { padding: 18, paddingBottom: 34 },
  hero: {
    backgroundColor: "#E4F0E8",
    padding: 24,
    borderRadius: 24,
  },
  eyebrow: {
    color: GREEN,
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 1.5,
  },
  heroTitle: {
    color: INK,
    fontSize: 29,
    lineHeight: 35,
    fontWeight: "800",
    marginTop: 14,
  },
  heroBody: { color: "#426456", lineHeight: 22, marginTop: 12 },
  spacer: { height: 10 },
  choice: {
    padding: 12,
    borderWidth: 1,
    borderColor: BORDER,
    borderRadius: 10,
    marginBottom: 7,
  },
  choiceSelected: {
    backgroundColor: "#E4F0E8",
    borderColor: GREEN,
  },
  choiceText: { color: INK, fontSize: 13 },
  choiceTextSelected: { color: GREEN, fontWeight: "800" },
  listItem: {
    paddingVertical: 15,
    borderBottomWidth: 1,
    borderColor: BORDER,
  },
  itemTitle: { color: INK, fontSize: 15, fontWeight: "800" },
  status: {
    color: GREEN,
    fontSize: 11,
    fontWeight: "800",
    marginTop: 8,
  },
  metric: {
    backgroundColor: "#F5F8F6",
    padding: 16,
    borderRadius: 14,
    marginBottom: 10,
  },
  metricValue: { color: INK, fontSize: 27, fontWeight: "800" },
  tabBar: {
    flexDirection: "row",
    flexWrap: "wrap",
    backgroundColor: "#FFFFFF",
    borderTopWidth: 1,
    borderColor: BORDER,
    paddingHorizontal: 6,
    paddingVertical: 7,
  },
  tab: {
    flexGrow: 1,
    paddingHorizontal: 8,
    paddingVertical: 10,
    alignItems: "center",
    borderRadius: 10,
  },
  tabActive: { backgroundColor: "#E4F0E8" },
  tabText: { color: MUTED, fontSize: 11, fontWeight: "600" },
  tabTextActive: { color: GREEN, fontWeight: "800" },
  busyOverlay: {
    position: "absolute",
    right: 18,
    top: 90,
    backgroundColor: "#FFFFFF",
    borderRadius: 24,
    padding: 12,
    elevation: 3,
  },
});
