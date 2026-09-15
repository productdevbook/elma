/**
 * DFU button sequences, which differ by hardware generation.
 *
 * Board identifiers are the only thing lockdown gives us, so the mapping is by
 * identifier rather than marketing name. Anything unrecognised falls back to
 * the Face ID sequence: every iPhone since 2017 uses it, so an unknown model
 * is far more likely to be newer than older.
 */

export type DfuFamily = 'faceid' | 'iphone7' | 'home'

export interface DfuStep {
  text: string
  /** Seconds the user must hold, when the step is timed. */
  hold?: number
}

export interface DfuGuide {
  family: DfuFamily
  label: string
  steps: DfuStep[]
}

const GUIDES: Record<DfuFamily, DfuGuide> = {
  faceid: {
    family: 'faceid',
    label: 'iPhone 8 and later',
    steps: [
      { text: 'Press and release Volume Up.' },
      { text: 'Press and release Volume Down.' },
      { text: 'Hold the Side button until the screen goes black.', hold: 10 },
      { text: 'Keep holding Side, and add Volume Down.', hold: 5 },
      { text: 'Release Side. Keep holding Volume Down.', hold: 10 },
    ],
  },
  iphone7: {
    family: 'iphone7',
    label: 'iPhone 7 and 7 Plus',
    steps: [
      { text: 'Hold Side and Volume Down together.', hold: 8 },
      { text: 'Release Side. Keep holding Volume Down.', hold: 10 },
    ],
  },
  home: {
    family: 'home',
    label: 'iPhone 6s and earlier',
    steps: [
      { text: 'Hold Home and the Side (or Top) button together.', hold: 8 },
      { text: 'Release Side. Keep holding Home.', hold: 10 },
    ],
  },
}

/** iPhone 7/7 Plus board ids — the only generation with its own sequence. */
const IPHONE_7 = new Set(['iPhone9,1', 'iPhone9,2', 'iPhone9,3', 'iPhone9,4'])

export function dfuGuideFor(productType: string | null): DfuGuide {
  if (!productType) return GUIDES.faceid
  if (IPHONE_7.has(productType)) return GUIDES.iphone7

  // iPhone1,1 through iPhone8,x have a Home button; iPhone10,x (iPhone 8 and X)
  // onward do not. iPads are keyed the same way by their own generation split.
  const m = /^(iPhone|iPad)(\d+),/.exec(productType)
  if (m) {
    const gen = Number(m[2])
    if (m[1] === 'iPhone' && gen <= 8) return GUIDES.home
    if (m[1] === 'iPad' && gen <= 7) return GUIDES.home
  }
  return GUIDES.faceid
}

/** Total seconds the sequence takes, for the progress ring. */
export function guideDuration(guide: DfuGuide): number {
  return guide.steps.reduce((n, s) => n + (s.hold ?? 0), 0)
}
