import { definePreset } from '@primeuix/themes'
import Aura from '@primeuix/themes/aura'

export const FinoPreset = definePreset(Aura, {
    primitive: {
        borderRadius: {
            none: '0',
            xs: '4px',
            sm: '6px',
            md: '8px',
            lg: '12px',
            xl: '16px',
        },

        finoRed: {
            50: '#FFF1F0',
            100: '#FFE0DD',
            200: '#FFBBB5',
            300: '#FF9188',
            400: '#FF6459',
            500: '#EF3124',
            600: '#DB2C20',
            700: '#C2271D',
            800: '#941C15',
            900: '#701510',
            950: '#440D09',
        },
    },

    semantic: {
        primary: {
            50: '{finoRed.50}',
            100: '{finoRed.100}',
            200: '{finoRed.200}',
            300: '{finoRed.300}',
            400: '{finoRed.400}',
            500: '{finoRed.500}',
            600: '{finoRed.600}',
            700: '{finoRed.700}',
            800: '{finoRed.800}',
            900: '{finoRed.900}',
            950: '{finoRed.950}',
        },

        formField: {
            paddingX: '1rem',
            paddingY: '0.75rem',
            borderRadius: '{border.radius.lg}',
        },

        colorScheme: {
            light: {
                primary: {
                    color: '{primary.500}',
                    contrastColor: '#ffffff',
                    hoverColor: '{primary.600}',
                    activeColor: '{primary.700}',
                },

                surface: {
                    0: '#ffffff',
                    50: '#f5f5f5',
                    100: '#ededed',
                    200: '#dadada',
                    300: '#bdbdbd',
                    400: '#8f8f8f',
                    500: '#4a4a4a',
                    600: '#3a3a3a',
                    700: '#2a2a2a',
                    800: '#1e1e1e',
                    900: '#111111',
                    950: '#0b0b0b',
                },

                text: {
                    color: '{surface.900}',
                    hoverColor: '{surface.950}',
                    mutedColor: '{surface.500}',
                    hoverMutedColor: '{surface.600}',
                },

                // Поля как в макете: белые, с чёрной обводкой; фокус — фиолетовым
                formField: {
                    background: '{surface.0}',
                    filledBackground: '{surface.0}',
                    filledHoverBackground: '{surface.0}',
                    filledFocusBackground: '{surface.0}',
                    borderColor: '#111111',
                    hoverBorderColor: '#111111',
                    focusBorderColor: '#8B2CF5',
                },
            },

            // Красный в тёмной теме на тон глубже: яркий #EF3124 на чёрном слишком кричит
            dark: {
                primary: {
                    color: '{primary.700}',
                    contrastColor: '#ffffff',
                    hoverColor: '{primary.600}',
                    activeColor: '{primary.800}',
                },

                surface: {
                    0: '#ffffff',
                    50: '#f4f4f4',
                    100: '#e0e0e0',
                    200: '#c4c4c4',
                    300: '#b8b8b8',
                    400: '#8f8f8f',
                    500: '#6b6b6b',
                    600: '#4a4a4a',
                    700: '#2e2e2e',
                    800: '#222222',
                    900: '#171717',
                    950: '#0b0b0b',
                },

                text: {
                    color: '{surface.0}',
                    hoverColor: '{surface.0}',
                    mutedColor: '{surface.400}',
                    hoverMutedColor: '{surface.300}',
                },

                formField: {
                    background: '{surface.900}',
                    filledBackground: '{surface.900}',
                    filledHoverBackground: '{surface.900}',
                    filledFocusBackground: '{surface.900}',
                    borderColor: '#4A4A4A',
                    hoverBorderColor: '#6B6B6B',
                    focusBorderColor: '#8B2CF5',
                },
            },
        },
    },

    components: {
        button: {
            root: {
                borderRadius: '{border.radius.lg}',
                paddingX: '1.25rem',
                paddingY: '0.75rem',
                label: {
                    fontWeight: '700',
                },
            },
        },

        inputtext: {
            root: {
                borderRadius: '14px',
            },
        },

        select: {
            root: {
                borderRadius: '14px',
            },
        },

        dialog: {
            root: {
                borderRadius: '24px',
                borderColor: '{text.color}',
            },
        },

        tag: {
            root: {
                borderRadius: '{border.radius.md}',
            },
        },

        // Поля — заливкой без рамки, а флажку и переключателю рамка нужна: серый квадрат на белом не видно
        checkbox: {
            colorScheme: {
                light: { root: { borderColor: '{surface.500}', hoverBorderColor: '{surface.700}' } },
                dark: { root: { borderColor: '{surface.500}', hoverBorderColor: '{surface.300}' } },
            },
        },

        radiobutton: {
            colorScheme: {
                light: { root: { borderColor: '{surface.500}', hoverBorderColor: '{surface.700}' } },
                dark: { root: { borderColor: '{surface.500}', hoverBorderColor: '{surface.300}' } },
            },
        },
    },
})
