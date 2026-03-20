export interface AuthStatusResponse {
  setup_required: boolean;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  message: string;
}

export interface RegisterRequest {
  username: string;
  password: string;
  email?: string;
}

export interface RegisterResponse {
  username: string;
  recovery_code: string;
}

export interface ResetPasswordRequest {
  recovery_code: string;
  new_password: string;
}

export interface ResetPasswordResponse {
  message: string;
  new_recovery_code: string;
}

export interface AuthErrorResponse {
  detail: {
    code: string;
  };
}

export interface UserResponse {
  id: number;
  username: string;
  email: string | null;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}
