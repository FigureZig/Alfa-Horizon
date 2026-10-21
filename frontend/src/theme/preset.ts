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
                    50: '#f3f4f5',
                    100: '#ebecef',
                    200: '#dbdee1',
                    300: '#c4c7cc',
                    400: '#a1a4ab',
                    500: '#75757e',
                    600: '#5c5e66',
                    700: '#43454c',
                    800: '#2c2d33',
                    900: '#212124',
                    950: '#0e0e10',
                },

                text: {
                    color: '{surface.900}',
                    hoverColor: '{surface.950}',
                    mutedColor: '{surface.500}',
                    hoverMutedColor: '{surface.600}',
                },

                formField: {
                    background: '{surface.50}',
                    filledBackground: '{surface.50}',
                    filledHoverBackground: '{surface.100}',
                    filledFocusBackground: '{surface.0}',
                    borderColor: '{surface.50}',
                    hoverBorderColor: '{surface.200}',
                    focusBorderColor: '{surface.900}',
                },
            },

            dark: {
                primary: {
                    color: '{primary.500}',
                    contrastColor: '#ffffff',
                    hoverColor: '{primary.400}',
                    activeColor: '{primary.600}',
                },

                surface: {
                    0: '#ffffff',
                    50: '#f3f4f5',
                    100: '#e1e2e6',
                    200: '#c6c7cc',
                    300: '#a1a2a8',
                    400: '#8d8d93',
                    500: '#6b6b72',
                    600: '#47474d',
                    700: '#333338',
                    800: '#26262b',
                    900: '#1c1c20',
                    950: '#121215',
                },

                text: {
                    color: '{surface.0}',
                    hoverColor: '{surface.0}',
                    mutedColor: '{surface.400}',
                    hoverMutedColor: '{surface.300}',
                },

                formField: {
                    background: '{surface.800}',
                    filledBackground: '{surface.800}',
                    filledHoverBackground: '{surface.700}',
                    filledFocusBackground: '{surface.800}',
                    borderColor: '{surface.800}',
                    hoverBorderColor: '{surface.600}',
                    focusBorderColor: '{surface.0}',
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
                    fontWeight: '500',
                },
            },
        },

        inputtext: {
            root: {
                borderRadius: '{border.radius.lg}',
            },
        },

        select: {
            root: {
                borderRadius: '{border.radius.lg}',
            },
        },

        dialog: {
            root: {
                borderRadius: '{border.radius.xl}',
            },
        },

        tag: {
            root: {
                borderRadius: '{border.radius.md}',
            },
        },
    },
})
