// Mirrors st_vtt/content.py and the character / shared-sheet documents.

export interface Stat { id: string; label: string; min: number; max: number }
export interface Debility { id: string; label: string; affects: string[]; text: string }
export interface Tier { label: string; min: number | null; max: number | null }
export interface RollRules { base: string; advantage: string; disadvantage: string; tiers: Tier[]; mark_xp_on: string[] }
export interface XpRules { level_up_cost: string; start_level: number; max_xp: number | null }
export interface DicePreset { label: string; expr: string }
export interface LoadRules { light: number; normal: number; heavy: number }
export interface PackMeta {
  id: string; name: string; description: string; stats: Stat[]; stat_array: number[];
  debilities: Debility[]; roll: RollRules; xp: XpRules; dice_presets: DicePreset[];
  load: LoadRules | null; gear_tags: string[]; hold_names: string[];
}
export interface RollSpec { stat: string | string[] | null; bonus: number; label: string | null }
export interface Hold { name: string; note: string }
export interface Requires { level: number | null; moves: string[] }
export interface Move {
  id: string; name: string; trigger: string; text: string; roll: RollSpec | null;
  outcomes: Record<string, string>; hold: Hold | null; pips: number | null;
  requires: Requires | null; tags: string[]; replaces: string | null;
}
export interface Effects { moves: string[]; armor: number | null; hp: number | null; tags: string[] }
export interface Option { id: string; label: string; text: string; effects: Effects | null; pips: number | null }
export interface Column { id: string; label: string; type: 'text' | 'number' | 'check' | 'select' | 'dice'; options: string[] }
export interface NameList { label: string; names: string[] }
export type SectionType = 'choose' | 'multichoose' | 'checklist' | 'pips' | 'text' | 'table' | 'names';
export interface Section {
  id: string; title: string; type: SectionType; help: string; options: Option[];
  min: number | null; max: number | null; columns: Column[]; lists: NameList[];
  placeholder: string; required: boolean;
}
export interface ChooseN { n: number; from: string[] }
export interface StartingMoves { fixed: string[]; choose: ChooseN[] }
export interface Playbook {
  id: string; name: string; blurb: string; hp_max: number; damage_die: string; armor: number;
  stat_array: number[] | null; sections: Section[]; moves: Move[]; starting_moves: StartingMoves;
  inserts: ('gear' | 'followers' | 'arcana')[]; hold_names: string[];
}
export interface FollowerRules { loyalty_max: number; tags: string[]; costs: string[]; instincts: string[]; fields: Column[] }
export interface Tracker { id: string; label: string; type: 'pips' | 'counter' | 'toggle'; max: number | null }
export interface Arcanum {
  id: string; name: string; kind: string; tags: string[]; description: string; questions: string[];
  prerequisites: string; moves: Move[]; trackers: Tracker[];
}
export interface SheetStat { id: string; label: string; start: number; min: number; max: number; help: string }
export interface SharedSheetDef {
  id: string; name: string; blurb: string; auto_create: boolean; visibility: 'table' | 'gm';
  stats: SheetStat[]; sizes: string[]; size_start: string | null;
  debilities: Debility[]; sections: Section[]; moves: Move[];
}
export interface ContentPack {
  pack: PackMeta; moves: Record<string, Move[]>; playbooks: Playbook[];
  followers: FollowerRules; arcana: Arcanum[]; shared_sheets: SharedSheetDef[];
}

// ---- documents

export interface Follower {
  id: string; name: string; tags: string[]; hp: { current: number; max: number }; armor: number;
  damage_die: string; instinct: string; cost: string; loyalty: number; moves: string; gear: string;
  notes: string; is_group: boolean; members: { name: string; hp: number }[]; fields: Record<string, unknown>;
}
export interface ArcanumInstance extends Omit<Arcanum, 'id'> {
  id: string; ref: string | null; answers: Record<string, string>; state: Record<string, number | boolean>; notes: string;
}
export interface GearItem { id: string; name: string; tags: string[]; weight: number; uses: { max: number; used: number } | null; notes: string }
export interface CharacterDoc {
  pack_id: string; playbook: string; name: string; pronouns: string; look: string;
  stats: Record<string, number>; hp: { current: number; max: number }; armor: number; xp: number; level: number;
  debilities: Record<string, boolean>;
  moves: { taken: string[]; pips: Record<string, number>; hold: Record<string, number> };
  sections: Record<string, unknown>;
  option_pips: Record<string, Record<string, number>>;
  gear: { load: number; items: GearItem[] };
  followers: Follower[]; arcana: ArcanumInstance[]; custom_moves: Move[];
  notes: string; gm_notes?: string; creation_done: boolean;
}
export interface CharacterRow { id: string; owner: string | null; revision: number; updated_at: number; data: CharacterDoc }
export interface SharedDoc {
  pack_id: string; template: string; name: string; stats: Record<string, number>; size: string; debilities: Record<string, boolean>;
  sections: Record<string, unknown>; option_pips: Record<string, Record<string, number>>;
  moves: { pips: Record<string, number>; hold: Record<string, number> };
  notes: string; gm_notes?: string;
}
export interface SharedRow { id: string; template: string; revision: number; created_at: number; updated_at: number; data: SharedDoc }

export interface User { name: string; role: 'gm' | 'player' }
export interface Message {
  id: number; ts: number; author: string | null; kind: 'chat' | 'whisper' | 'roll' | 'system' | 'request' | 'move';
  payload: any; visibility: string[] | null;
}
export interface StateResponse {
  me: User; campaign_name: string; users: User[]; online: string[];
  characters: CharacterRow[]; shared: SharedRow[]; messages: Message[];
}
