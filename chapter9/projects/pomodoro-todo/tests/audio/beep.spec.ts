import { describe, it, expect, afterEach, vi } from 'vitest'
import { playBeep } from '../../src/audio/beep'

describe('playBeep', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('AudioContext가 없으면 예외 없이 끝난다', () => {
    vi.stubGlobal('AudioContext', undefined)
    vi.stubGlobal('webkitAudioContext', undefined)
    expect(() => playBeep()).not.toThrow()
  })

  it('생성자가 throw해도 예외 없이 끝난다', () => {
    vi.stubGlobal(
      'AudioContext',
      function () {
        throw new Error('boom')
      },
    )
    expect(() => playBeep()).not.toThrow()
  })

  it('정상 stub이면 oscillator start를 1회 호출한다', () => {
    const start = vi.fn()
    const osc = {
      type: '',
      frequency: { value: 0 },
      connect: vi.fn(),
      start,
      stop: vi.fn(),
      onended: null,
    }
    const gain = { gain: { value: 0 }, connect: vi.fn() }
    vi.stubGlobal(
      'AudioContext',
      function () {
        return {
          createOscillator: () => osc,
          createGain: () => gain,
          destination: {},
          currentTime: 0,
          close: vi.fn(),
        }
      },
    )
    playBeep()
    expect(start).toHaveBeenCalledTimes(1)
  })
})
