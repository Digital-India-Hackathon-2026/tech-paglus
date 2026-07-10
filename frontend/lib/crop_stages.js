// Per-crop production journey — used by the crop detail / production-plan page.
// Every crop gets its own tailored set of stages and steps (seed selection ->
// harvesting), built from the crop knowledge base plus curated overrides for
// the most commonly recommended crops.

import { CROPS } from './crop_kb';

function findCrop(id) {
  return CROPS.find((c) => c.id === id);
}

const WATER_ADVICE = {
  low: 'Light, infrequent irrigation — protect against waterlogging and rely on residual soil moisture where possible.',
  medium: 'Moderate irrigation on a regular cycle — keep the root zone moist but never waterlogged.',
  high: 'Frequent, generous irrigation — this crop is sensitive to moisture stress at every stage.',
};

const SEASON_LABEL = { kharif: 'Kharif (monsoon)', rabi: 'Rabi (winter)', summer: 'Summer', annual: 'Year-round' };

// Curated overrides for crops that appear in the recommendation screen most often.
const OVERRIDES = {
  chilli: {
    duration: '150-180 days',
    stages: [
      {
        key: 'seed',
        title: 'Seed Selection',
        summary: 'Choose a certified, disease-resistant chilli variety suited to red soil.',
        steps: [
          'Pick a certified hybrid such as Teja or Byadgi based on local mandi demand.',
          'Buy seed only from a licensed dealer and check the lot/batch number.',
          'Treat seed with Trichoderma or a fungicide before nursery sowing.',
          'Raise a nursery in raised beds 30-35 days before transplanting.',
        ],
      },
      {
        key: 'landprep',
        title: 'Land Preparation & Sowing',
        summary: 'Prepare beds and transplant healthy seedlings at the right spacing.',
        steps: [
          'Plough the field 2-3 times and add well-rotted farmyard manure.',
          'Form raised beds/ridges for good drainage — chilli dislikes standing water.',
          'Transplant seedlings at 45cm x 45cm spacing on a cool evening.',
          'Apply basal fertilizer (NPK) at the time of transplanting.',
        ],
      },
      {
        key: 'water',
        title: 'Water Requirement',
        summary: WATER_ADVICE.medium,
        steps: [
          'Irrigate immediately after transplanting, then every 7-10 days.',
          'Switch to drip irrigation if available — it cuts water use by 30-40%.',
          'Avoid overhead irrigation during flowering to reduce fruit rot risk.',
          'Stop irrigation 2-3 weeks before final harvest to concentrate pungency.',
        ],
      },
      {
        key: 'nutrition',
        title: 'Fertilizer & Nutrition',
        summary: 'Split fertilizer doses across the growth cycle for steady fruiting.',
        steps: [
          'Apply calcium nitrate in split doses to support fruit set.',
          'Add a micronutrient spray (boron/zinc) at flowering stage.',
          'Use neem cake to improve soil health and deter soil pests.',
        ],
      },
      {
        key: 'pest',
        title: 'Pest & Disease Management',
        summary: 'Watch for thrips, mites and fruit rot — chilli\'s main threats.',
        steps: [
          'Install yellow/blue sticky traps to monitor thrips and mites early.',
          'Spray neem oil at the first sign of leaf curling.',
          'Remove and destroy infected fruit to stop fruit rot spreading.',
          'Avoid spraying just before rain — it washes off and wastes input cost.',
        ],
      },
      {
        key: 'harvest',
        title: 'Harvesting',
        summary: 'Harvest in rounds as pods ripen for the best mandi price.',
        steps: [
          'Begin harvesting once pods turn deep red and slightly dry at the stalk.',
          'Pick in 8-10 rounds every 7-10 days rather than a single harvest.',
          'Dry harvested chilli on a clean tarpaulin, not directly on soil.',
          'Grade by size/colour before taking to mandi for a better price.',
        ],
      },
    ],
  },
  groundnut: {
    duration: '100-130 days',
    stages: [
      {
        key: 'seed',
        title: 'Seed Selection',
        summary: 'Choose bold, disease-free kernels of a variety suited to sandy loam soil.',
        steps: [
          'Select a variety such as Kadiri or Dharani based on regional performance.',
          'Use bold, uniform kernels with over 70% germination.',
          'Treat seed with Rhizobium culture to boost natural nitrogen fixation.',
          'Treat with Trichoderma to reduce collar rot risk.',
        ],
      },
      {
        key: 'landprep',
        title: 'Land Preparation & Sowing',
        summary: 'Loosen soil well — groundnut pegs need to penetrate easily.',
        steps: [
          'Deep plough and harrow to create fine, loose soil.',
          'Sow at 30cm x 10cm spacing at 4-5cm depth.',
          'Ensure good drainage; groundnut is sensitive to waterlogging.',
        ],
      },
      {
        key: 'water',
        title: 'Water Requirement',
        summary: WATER_ADVICE.medium,
        steps: [
          'Keep soil moist at sowing and again at pegging/flowering stage.',
          'Avoid irrigation right before harvest to keep pods clean and dry.',
          'Critical stages for water: flowering, pegging and pod development.',
        ],
      },
      {
        key: 'nutrition',
        title: 'Fertilizer & Nutrition',
        summary: 'Gypsum at flowering is the single most impactful input.',
        steps: [
          'Apply gypsum at the start of flowering to support pod filling.',
          'Avoid excess nitrogen — it promotes leaf growth over pod yield.',
        ],
      },
      {
        key: 'pest',
        title: 'Pest & Disease Management',
        summary: 'Leaf spot and aflatoxin are the biggest risks after humid weather.',
        steps: [
          'Scout for leaf spot after rain and spray a recommended fungicide if seen.',
          'Avoid water stagnation, which encourages fungal disease.',
          'Dry pods properly after harvest to avoid aflatoxin contamination.',
        ],
      },
      {
        key: 'harvest',
        title: 'Harvesting',
        summary: 'Time the harvest carefully — too early or late both reduce quality.',
        steps: [
          'Check maturity by pulling a few plants — pods should have dark veins inside.',
          'Harvest when 70-80% of pods are mature.',
          'Dry pods to 8-9% moisture before storage or sale.',
        ],
      },
    ],
  },
  turmeric: {
    duration: '210-270 days',
    stages: [
      {
        key: 'seed',
        title: 'Seed (Rhizome) Selection',
        summary: 'Turmeric is planted from disease-free mother/finger rhizomes.',
        steps: [
          'Select healthy rhizomes such as Pragati with 2-3 buds each.',
          'Treat rhizomes with Trichoderma or a fungicide solution before planting.',
          'Avoid rhizomes with soft spots or shrivelling — sign of rot.',
        ],
      },
      {
        key: 'landprep',
        title: 'Land Preparation & Planting',
        summary: 'Turmeric needs a well-drained, well-worked bed.',
        steps: [
          'Plough to a fine tilth and form ridges/raised beds.',
          'Plant rhizomes at 30cm x 25cm spacing, 5cm deep.',
          'Mulch immediately after planting to conserve moisture and suppress weeds.',
        ],
      },
      {
        key: 'water',
        title: 'Water Requirement',
        summary: WATER_ADVICE.medium,
        steps: [
          'Irrigate immediately after planting, then every 7-15 days depending on rainfall.',
          'Ensure good drainage — waterlogging causes rhizome rot.',
          'Reduce watering as leaves start yellowing near maturity.',
        ],
      },
      {
        key: 'nutrition',
        title: 'Fertilizer & Nutrition',
        summary: 'Neem cake and organic matter build long-season soil health.',
        steps: [
          'Apply neem cake at planting for pest suppression and soil health.',
          'Top-dress with a balanced NPK mix at 60 and 120 days.',
          'Earth up (mound soil around plants) after each fertilizer dose.',
        ],
      },
      {
        key: 'pest',
        title: 'Pest & Disease Management',
        summary: 'Rhizome rot in poorly drained fields is the main risk.',
        steps: [
          'Improve field drainage at the first sign of yellowing leaves.',
          'Remove and destroy affected clumps immediately to stop spread.',
          'Watch for leaf blotch after prolonged humid weather.',
        ],
      },
      {
        key: 'harvest',
        title: 'Harvesting',
        summary: 'Turmeric is a long-duration crop — patience improves yield and colour.',
        steps: [
          'Harvest 7-9 months after planting when leaves dry and turn yellow-brown.',
          'Dig up rhizomes carefully to avoid cutting or bruising.',
          'Boil, dry and polish rhizomes before taking to market for the best price.',
        ],
      },
    ],
  },
};

// Generic template used for any crop without a curated override, built from
// the crop's own attributes (water need, season, common pests).
function buildGenericStages(crop) {
  const water = WATER_ADVICE[crop?.water] || WATER_ADVICE.medium;
  const pests = crop?.riskPests?.length ? crop.riskPests.join(', ') : 'common local pests and diseases';
  const seasonLabel = SEASON_LABEL[crop?.seasons?.[0]] || 'the recommended season';
  return [
    {
      key: 'seed',
      title: 'Seed Selection',
      summary: `Pick certified, high-germination seed suited to ${crop?.soils?.[0]?.replace('_', ' ') || 'your soil type'}.`,
      steps: [
        'Buy certified seed from a licensed dealer — check the lot/batch number.',
        'Choose a variety recommended for your district and this season.',
        'Treat seed with a fungicide/bio-agent before sowing to prevent early disease.',
        'Check germination rate on a small sample before full sowing.',
      ],
    },
    {
      key: 'landprep',
      title: 'Land Preparation & Sowing',
      summary: `Prepare the field for ${seasonLabel} sowing with good drainage and tilth.`,
      steps: [
        'Plough and level the field, removing old crop residue and weeds.',
        'Apply well-rotted farmyard manure or compost before sowing.',
        'Sow at the recommended spacing and depth for this crop.',
        'Apply basal fertilizer at sowing/transplanting time.',
      ],
    },
    {
      key: 'water',
      title: 'Water Requirement',
      summary: water,
      steps: [
        'Irrigate soon after sowing/transplanting to establish the crop.',
        'Follow a regular irrigation cycle through vegetative growth.',
        'Increase attentiveness during flowering and grain/fruit filling — the most water-sensitive stage.',
        'Reduce or stop irrigation as the crop nears maturity.',
      ],
    },
    {
      key: 'nutrition',
      title: 'Fertilizer & Nutrition',
      summary: 'Split fertilizer doses to match crop growth stages.',
      steps: [
        'Apply basal fertilizer at sowing based on soil test values.',
        'Top-dress with nitrogen/potash at key growth stages.',
        'Use a micronutrient spray if leaves show yellowing or poor growth.',
      ],
    },
    {
      key: 'pest',
      title: 'Pest & Disease Management',
      summary: `Watch for ${pests} through the growing season.`,
      steps: [
        'Scout the field twice a week for early signs of pest or disease damage.',
        'Use sticky traps or pheromone traps where available for early warning.',
        'Spray only recommended crop-protection products, avoiding overuse.',
        'Avoid spraying right before expected rain.',
      ],
    },
    {
      key: 'harvest',
      title: 'Harvesting',
      summary: 'Harvest at the right maturity stage to protect both yield and price.',
      steps: [
        'Check maturity signs specific to this crop before harvesting.',
        'Harvest in dry weather where possible to reduce post-harvest loss.',
        'Dry and clean produce properly before storage or sale.',
        'Grade produce before taking it to market for a better price.',
      ],
    },
  ];
}

export function getCropStages(cropId) {
  const crop = findCrop(cropId);
  const override = OVERRIDES[cropId];
  const stages = override?.stages || buildGenericStages(crop);
  return {
    id: cropId,
    name: crop?.name || cropId,
    name_te: crop?.te,
    name_hi: crop?.hi,
    duration: override?.duration || 'Varies by variety and region',
    season: SEASON_LABEL[crop?.seasons?.[0]] || 'Season-dependent',
    water: crop?.water || 'medium',
    stages,
  };
}

export function getStorageKey(cropId, sessionId) {
  return `agri_progress_${sessionId || 'default'}_${cropId}`;
}
