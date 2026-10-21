import axios from 'axios'

export function useApiFetch() {
    const axiosIns = axios.create({
        baseURL: import.meta.env.VITE_API_BASE_URL,
        timeout: 15000,
        headers: {
            Accept: 'application/json',
        },
    })

    return axiosIns
}