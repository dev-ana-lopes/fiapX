export interface RegisterRequest {
  name: string;
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string | null;
  token_type: string;
}

export interface CurrentUser {
  id: string;
  name: string;
  email: string;
}
