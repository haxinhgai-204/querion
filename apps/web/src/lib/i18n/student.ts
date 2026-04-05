export type Locale = "en" | "vi";

export const translations = {
  en: {
    // Auth
    login: "Login",
    email: "Email",
    password: "Password",
    loginTitle: "Student Login",
    loginSubtitle: "Sign in to access your apps",
    loginButton: "Sign In",
    loginError: "Invalid email or password",
    logout: "Logout",

    // Change password
    changePasswordTitle: "Change Password",
    changePasswordSubtitle: "You must change your password before continuing",
    currentPassword: "Current Password",
    newPassword: "New Password",
    confirmPassword: "Confirm Password",
    changePasswordButton: "Change Password",
    passwordMismatch: "Passwords do not match",
    passwordTooShort: "Password must be at least 6 characters",

    // Chat
    selectApp: "Select an app",
    selectAppSubtitle: "Choose an app from the sidebar to start chatting",
    newChat: "+ New Chat",
    typeMessage: "Type a message...",
    send: "Send",
    noApps: "No apps available",
    startConversation: "Start a conversation with",
    connectionError: "Connection error.",
    noResponse: "No response received.",
    workflowError: "Workflow error",

    // Theme
    darkMode: "Dark mode",
    lightMode: "Light mode",

    // General
    language: "Language",
  },
  vi: {
    // Auth
    login: "Đăng nhập",
    email: "Email",
    password: "Mật khẩu",
    loginTitle: "Đăng nhập Sinh viên",
    loginSubtitle: "Đăng nhập để truy cập ứng dụng",
    loginButton: "Đăng nhập",
    loginError: "Email hoặc mật khẩu không đúng",
    logout: "Đăng xuất",

    // Change password
    changePasswordTitle: "Đổi mật khẩu",
    changePasswordSubtitle: "Bạn cần đổi mật khẩu trước khi tiếp tục",
    currentPassword: "Mật khẩu hiện tại",
    newPassword: "Mật khẩu mới",
    confirmPassword: "Xác nhận mật khẩu",
    changePasswordButton: "Đổi mật khẩu",
    passwordMismatch: "Mật khẩu không khớp",
    passwordTooShort: "Mật khẩu phải có ít nhất 6 ký tự",

    // Chat
    selectApp: "Chọn ứng dụng",
    selectAppSubtitle: "Chọn một ứng dụng từ menu bên trái để bắt đầu",
    newChat: "+ Cuộc trò chuyện mới",
    typeMessage: "Nhập tin nhắn...",
    send: "Gửi",
    noApps: "Không có ứng dụng nào",
    startConversation: "Bắt đầu trò chuyện với",
    connectionError: "Lỗi kết nối.",
    noResponse: "Không nhận được phản hồi.",
    workflowError: "Lỗi quy trình",

    // Theme
    darkMode: "Chế độ tối",
    lightMode: "Chế độ sáng",

    // General
    language: "Ngôn ngữ",
  },
} as const;

export type TranslationKey = keyof typeof translations.en;
