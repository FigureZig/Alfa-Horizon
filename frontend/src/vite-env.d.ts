/// <reference types="vite/client" />

interface ImportMetaEnv {
    readonly VITE_API_BASE_URL: string
    readonly FEATURE_K1?: string
    readonly FEATURE_K2?: string
}

interface ImportMeta {
    readonly env: ImportMetaEnv
}