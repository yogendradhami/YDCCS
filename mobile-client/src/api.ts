
import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

const BASE_URL = process.env.EXPO_PUBLIC_API_URL?.replace(/\/+$/, "");

if (!BASE_URL) {
  console.warn("EXPO_PUBLIC_API_URL is not configured.");
}

const ACCESS_KEY = "yd_access_token";
const REFRESH_KEY = "yd_refresh_token";

/**
 * Store tokens using native SecureStore on iOS/Android.
 * Web preview uses localStorage because SecureStore's native
 * storage methods are not available in the browser.
 */
async function getStoredItem(key: string): Promise<string | null> {
  if (Platform.OS === "web") {
    if (typeof localStorage === "undefined") return null;
    return localStorage.getItem(key);
  }

  return SecureStore.getItemAsync(key);
}

async function setStoredItem(
  key: string,
  value: string
): Promise<void> {
  if (Platform.OS === "web") {
    if (typeof localStorage === "undefined") {
      throw new Error("Browser storage is unavailable.");
    }

    localStorage.setItem(key, value);
    return;
  }

  await SecureStore.setItemAsync(key, value);
}

async function deleteStoredItem(key: string): Promise<void> {
  if (Platform.OS === "web") {
    if (typeof localStorage !== "undefined") {
      localStorage.removeItem(key);
    }
    return;
  }

  await SecureStore.deleteItemAsync(key);
}

export async function saveTokens(
  access: string,
  refresh: string
): Promise<void> {
  await setStoredItem(ACCESS_KEY, access);
  await setStoredItem(REFRESH_KEY, refresh);
}

export async function clearTokens(): Promise<void> {
  await Promise.all([
    deleteStoredItem(ACCESS_KEY),
    deleteStoredItem(REFRESH_KEY),
  ]);
}

async function refreshAccessToken(): Promise<string | null> {
  const refresh = await getStoredItem(REFRESH_KEY);

  if (!refresh || !BASE_URL) return null;

  try {
    const response = await fetch(`${BASE_URL}/auth/token/refresh/`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ refresh }),
    });

    if (!response.ok) {
      await clearTokens();
      return null;
    }

    const data: { access?: string; refresh?: string } =
      await response.json();

    if (!data.access) {
      await clearTokens();
      return null;
    }

    await setStoredItem(ACCESS_KEY, data.access);

    // Support SimpleJWT refresh-token rotation when enabled.
    if (data.refresh) {
      await setStoredItem(REFRESH_KEY, data.refresh);
    }

    return data.access;
  } catch {
    return null;
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  authenticated = true
): Promise<T> {
  if (!BASE_URL) {
    throw new Error("API URL is not configured.");
  }

  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  const send = async (token?: string | null): Promise<Response> => {
    const headers = new Headers(options.headers);

    headers.set("Accept", "application/json");

    const isFormData =
      typeof FormData !== "undefined" && options.body instanceof FormData;

    if (options.body && !isFormData && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    } else {
      headers.delete("Authorization");
    }

    return fetch(`${BASE_URL}${normalizedPath}`, {
      ...options,
      headers,
    });
  };

  let token = authenticated
    ? await getStoredItem(ACCESS_KEY)
    : null;

  let response = await send(token);

  if (response.status === 401 && authenticated) {
    token = await refreshAccessToken();

    if (token) {
      response = await send(token);
    } else {
      await clearTokens();
    }
  }

  const data: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const body =
      data && typeof data === "object"
        ? (data as Record<string, unknown>)
        : null;

    const detail = body?.detail ?? body?.message;

    const validationMessages =
      body && !detail
        ? Object.values(body)
            .flatMap((value) =>
              Array.isArray(value) ? value : [value]
            )
            .filter(
              (value): value is string => typeof value === "string"
            )
            .join(" ")
        : "";

    const message =
      (typeof detail === "string" ? detail : null) ||
      validationMessages ||
      `Request failed (${response.status})`;

    throw new Error(message);
  }

  return data as T;
}

export async function signIn(
  username: string,
  password: string
): Promise<void> {
  const data = await apiRequest<{
    access: string;
    refresh: string;
  }>(
    "/auth/token/",
    {
      method: "POST",
      body: JSON.stringify({ username, password }),
    },
    false
  );

  await saveTokens(data.access, data.refresh);
}

export async function registerCustomer(input: {
  full_name: string;
  email: string;
  phone: string;
  password: string;
}): Promise<{ message: string }> {
  return apiRequest<{ message: string }>(
    "/auth/register/",
    {
      method: "POST",
      body: JSON.stringify(input),
    },
    false
  );
}

export async function getMe() {
  return apiRequest<{
    user: {
      id: number;
      username: string;
      email: string;
      first_name: string;
      last_name: string;
      is_staff: boolean;
      is_superuser: boolean;
    };
    roles: string[];
    customer: {
      id: number;
      full_name: string;
      email: string;
      phone: string;
      address: string;
      suburb_postcode: string;
    } | null;
    employee: {
      id: number;
      full_name: string;
      role: string;
    } | null;
  }>("/me/");
}
