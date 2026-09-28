import { MotionConfig } from "framer-motion";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import ToastViewport from "@/components/common/ToastViewport";
import AppLayout from "@/components/layout/AppLayout";
import { AppProvider } from "@/context/AppContext";
import { AuthProvider } from "@/context/AuthContext";
import { ThemeProvider } from "@/context/ThemeContext";
import ChatPage from "@/pages/ChatPage";
import DocumentsPage from "@/pages/DocumentsPage";
import HomePage from "@/pages/HomePage";
import LoginPage from "@/pages/LoginPage";

export default function App() {
  return (
    <MotionConfig reducedMotion="user">
      <ThemeProvider>
        <BrowserRouter>
        <AuthProvider>
          <AppProvider>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<LoginPage initialMode="register" />} />
              <Route
                path="/app"
                element={
                  <ProtectedRoute>
                    <AppLayout />
                  </ProtectedRoute>
                }
              >
                <Route index element={<Navigate to="home" replace />} />
                <Route path="home" element={<HomePage />} />
                <Route path="documents" element={<DocumentsPage />} />
                <Route path="chat" element={<Navigate to="/app/documents" replace />} />
                <Route path="chat/:sessionId" element={<ChatPage />} />
              </Route>
              <Route path="/" element={<Navigate to="/app/home" replace />} />
              <Route path="*" element={<Navigate to="/app/home" replace />} />
            </Routes>
            <ToastViewport />
          </AppProvider>
        </AuthProvider>
        </BrowserRouter>
      </ThemeProvider>
    </MotionConfig>
  );
}
