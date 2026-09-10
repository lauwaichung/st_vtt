import type { Move } from './types';

export interface RollRequest {
  characterId: string | null;
  move: Move | null;
  stat?: string | null;
  label?: string;
  bonus?: number;
}

export const dialogs = $state({
  roll: null as RollRequest | null,
});

export function openRoll(req: RollRequest): void {
  dialogs.roll = req;
}
