
import * as SecureStore from "expo-secure-store";

const BASE_URL = process.env.EXPO_PUBLIC_API_URL;

if (!BASE_URL) {
  console.warn("EXPO_PUBLIC_API_URL is not configured.");
}

const ACCESS_KEY = "yd_access_token";
const REFRESH_KEY = "yd_refresh_token";

export async function saveTokens(
  access: string,
  refresh: string
) {
  await SecureStore.setItemAsync(ACCESS_KEY, access);
  await SecureStore.setItemAsync(REFRESH_KEY, refresh);
}

export async function clearTokens() {
  await SecureStore.deleteItemAsync(ACCESS_KEY);
  await SecureStore.deleteItemAsync(REFRESH_KEY);
}

async function refreshAccessToken(): Promise<string | null> {
  const refresh = await SecureStore.getItemAsync(REFRESH_KEY);

  if (!refresh || !BASE_URL) return null;

  try {
    const response = await fetch(`${BASE_URL}/auth/token/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
    });

    if (!response.ok) {
      await clearTokens();
      return null;
    }

    const data = await response.json();
    await SecureStore.setItemAsync(ACCESS_KEY, data.access);

    // SimpleJWT can rotate refresh tokens when configured to do so.
    if (data.refresh) {
      await SecureStore.setItemAsync(REFRESH_KEY, data.refresh);
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

  const send = async (token?: string | null) => {
    const headers = new Headers(options.headers);
    headers.set("Accept", "application/json");

    if (options.body && !(options.body instanceof FormData)) {
      headers.set("Content-Type", "application/json");
    }

    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }

    return fetch(`${BASE_URL}${path}`, {
      ...options,
      headers,
    });
  };

  let token = authenticated
    ? await SecureStore.getItemAsync(ACCESS_KEY)
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

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const message =
      data?.detail ||
      data?.message ||
      (typeof data === "object" && data
        ? Object.values(data).flat().join(" ")
        : null) ||
      `Request failed (${response.status})`;

    throw new Error(String(message));
  }

  return data as T;
}

export async function signIn(username: string, password: string) {
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
}) {
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
