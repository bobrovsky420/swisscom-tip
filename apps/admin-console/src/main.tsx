import React from "react";
import ReactDOM from "react-dom/client";
import { MantineProvider, createTheme } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "@mantine/core/styles.css";
import "./styles.css";
import { App } from "./App";

const theme = createTheme({
  primaryColor: "teal",
  defaultRadius: "md",
  fontFamily: "Inter, Segoe UI, sans-serif",
  headings: { fontFamily: "Inter, Segoe UI, sans-serif", fontWeight: "600" },
});
const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false, refetchOnWindowFocus: false },
    mutations: { retry: false },
  },
});
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <MantineProvider theme={theme}>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </MantineProvider>
  </React.StrictMode>,
);
