export type PositionGroup = "CB" | "FB" | "CM" | "AM_W" | "ST" | "GK";

export type Player = {
  id: string;
  name: string;
  birthYear: number | null;
  nationality: string | null;
  flag: string;
  team: string;
  league: string | null;
  season: number;
  seasonLabel: string;
  age: number | null;
  positionGroup: PositionGroup | string;
  position: string;
  subPosition: string | null;
  minutes: number | null;
  marketValueEur: number | null;
  predictedValueEur: number | null;
  calibratedGap: number | null;
  style: string | null;
  percentiles: Record<string, number | null>;
};

export type SearchHit = {
  id: string;
  name: string;
  team: string;
  position: string;
  positionGroup: string;
};

export type Neighbor = { id: string; similarity: number };

export type PcaPoint = { id: string; x: number; y: number; style: string | null };

export type Cluster = {
  positionGroup: string;
  position: string;
  id: number;
  name: string;
  size: number;
  moreOf: string;
  lessOf: string;
  typicalPlayers: string[];
};

export type SquadPlayer = {
  id: string;
  name: string;
  positionGroup: string;
  style: string | null;
  has2526Point: boolean;
  inPlayers: boolean;
};

export type PredictionPoint = {
  id: string;
  actual: number;
  predicted: number;
  calibratedGap: number | null;
  decile: number | null;
};

export type Decile = {
  decile: number;
  players: number;
  meanLogGap: number | null;
  low: number | null;
  high: number | null;
};

export type BacktestWindow = {
  window: string;
  picks: number | null;
  signings: number | null;
  ageMatched: number | null;
  roleBaseline: number | null;
};

export type BacktestPick = {
  id: string | null;
  name: string;
  team: string;
  window: string;
  positionGroup: string | null;
  age: number | null;
  rank: number;
  marketValueEur: number | null;
  modelValueEur: number | null;
  calibratedGap: number | null;
  valueChangePct: number | null;
};

export type BacktestSigning = {
  id: string | null;
  name: string;
  from: string | null;
  window: string;
  positionGroup: string | null;
  feeEur: number | null;
  isLoan: boolean | null;
  valueAtWindowEur: number | null;
  modelValueEur: number | null;
  gap: number | null;
  gapPercentile: number | null;
  minutesShare: number | null;
  scorable: boolean | null;
  outcome: string | null;
  tier: string | null;
  valueChangePct: number | null;
};

export type NeedComponents = {
  quality: number | null;
  output: number | null;
  depth: number | null;
  age: number | null;
  contract: number | null;
};

export type NeedRaw = {
  spursDepth: number | null;
  benchmarkDepth: number | null;
  spursQualityEur: number | null;
  benchmarkQualityEur: number | null;
  outputPercentile: number | null;
  ageShare: number | null;
  contractShare: number | null;
};

export type Need = {
  positionGroup: string;
  position: string;
  needScore: number;
  rank: number;
  targetStyle: string | null;
  stylesPresent: string | null;
  stylesMissing: string | null;
  outputPercentile: number | null;
  components: NeedComponents;
  raw: NeedRaw;
};

export type NeedsSensitivityPosition = {
  positionGroup: string;
  needScoreEqual: number | null;
  needScoreQuality50: number | null;
  rankEqual: number;
  rankQuality50: number;
};

export type NeedsSensitivity = {
  top2EqualWeightsChanged: boolean;
  top2Quality50Changed: boolean;
  positions: NeedsSensitivityPosition[];
};

export type NeedsData = {
  positions: Need[];
  needsSensitivity: NeedsSensitivity;
};

export type ShortlistRow = {
  id: string | null;
  need: string;
  rank: number;
  name: string;
  club: string;
  age: number | null;
  targetStyle: string | null;
  marketValueEur: number | null;
  predictedValueEur: number | null;
  totalScore: number | null;
  valuePercentile: number | null;
  stylePercentile: number | null;
  formPercentile: number | null;
  reliabilityPercentile: number | null;
  flags: string | null;
};

export type StoryPlayer = {
  id: string;
  name: string;
  style: string | null;
  position: string;
  team: string;
  age: number | null;
  marketValueEur: number | null;
};

export type ModelMetricRow = {
  model: string;
  split: "grouped_by_player" | "time_split_2025_26";
  r2: number;
  mae_log: number;
  median_pct_error: number;
};

export type ModelMetrics = {
  rows: ModelMetricRow[];
  keptModel: string;
  keptReason: string;
};

export type Meta = {
  playersAnalyzed: number;
  seasons: number;
  leagues: number;
  poolSeason: string;
  poolPlayers: number;
  r2: number;
  typicalMissPct: number;
  headlines: {
    picksMedianPct: number;
    ageMatchedPct: number;
    beatSharePct: number;
    signingsMedianPct: number;
  };
  examples: { palhinha: StoryPlayer; porro: StoryPlayer };
  featureLabels: Record<string, string>;
  roles: Record<string, string>;
};
