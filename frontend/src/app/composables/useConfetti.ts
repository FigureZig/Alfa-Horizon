// Хлопушка: цветные квадратики и полоски разлетаются из элемента и падают — как в макете
const PIECE_COUNT = 32
const COLORS = ['var(--p-primary-color)', 'var(--fino-lime)', 'var(--fino-violet)', 'var(--fino-blue)', 'var(--fino-amber)']

function random(min: number, max: number): number {
  return min + Math.random() * (max - min)
}

export function useConfetti() {
  function burst(origin: HTMLElement) {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    const rect = origin.getBoundingClientRect()
    const x = rect.left + rect.width / 2
    const y = rect.top + rect.height / 2

    for (let index = 0; index < PIECE_COUNT; index += 1) {
      const piece = document.createElement('span')
      const isStrip = index % 3 === 0
      const size = random(8, 13)

      Object.assign(piece.style, {
        position: 'fixed',
        left: `${x}px`,
        top: `${y}px`,
        width: `${isStrip ? 5 : size}px`,
        height: `${isStrip ? 16 : size}px`,
        background: COLORS[index % COLORS.length],
        border: '2px solid #111',
        borderRadius: index % 4 === 0 ? '50%' : '2px',
        pointerEvents: 'none',
        zIndex: '60',
      })

      document.body.append(piece)

      // Веер вверх: ±75° от вертикали, потом гравитация тянет вниз
      const angle = random(-165, -15) * (Math.PI / 180)
      const speed = random(140, 320)
      const dx = Math.cos(angle) * speed
      const dy = Math.sin(angle) * speed
      const spin = random(-540, 540)

      const animation = piece.animate(
        [
          { transform: 'translate(-50%, -50%) rotate(0deg) scale(0.4)', opacity: 1 },
          { transform: `translate(${dx}px, ${dy}px) rotate(${spin / 2}deg) scale(1)`, opacity: 1, offset: 0.45 },
          { transform: `translate(${dx * 1.25}px, ${dy + random(240, 380)}px) rotate(${spin}deg) scale(0.9)`, opacity: 0 },
        ],
        { duration: random(950, 1400), easing: 'cubic-bezier(0.2, 0.7, 0.4, 1)' },
      )

      animation.onfinish = () => piece.remove()
    }
  }

  return { burst }
}
