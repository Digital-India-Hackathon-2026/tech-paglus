// Crop Knowledge Base — used by recommendation engine, advisory, mandi estimator
// Every value here is a *transparent estimate*, tunable, and drives location-varying output.

export const CROPS = [
  { id:'rice', name:'Rice (Paddy)', te:'వరి', hi:'धन (चावल)', soils:['clay','black','alluvial','red_loam'], seasons:['kharif','rabi'], water:'high',
    statesHigh:['telangana','andhra pradesh','west bengal','punjab','tamil nadu','odisha','uttar pradesh','bihar','chhattisgarh'], statesMed:['karnataka','maharashtra','haryana','assam'],
    basePrice:2200, demand:0.75, oversupplyStates:['punjab','west bengal'], inputCost:35000, revenue:70000, riskPests:['blast','brown planthopper'] },
  { id:'cotton', name:'Cotton', te:'పిత్తి', hi:'कपास', soils:['black','red','red_loam'], seasons:['kharif'], water:'medium',
    statesHigh:['telangana','maharashtra','gujarat','andhra pradesh','karnataka'], statesMed:['tamil nadu','madhya pradesh','haryana'],
    basePrice:7200, demand:0.7, oversupplyStates:['gujarat'], inputCost:45000, revenue:95000, riskPests:['pink bollworm','whitefly'] },
  { id:'maize', name:'Maize (Corn)', te:'మొక్కజొన్న', hi:'मक्का', soils:['loam','red','alluvial','red_loam','black'], seasons:['kharif','rabi'], water:'medium',
    statesHigh:['karnataka','telangana','bihar','madhya pradesh','andhra pradesh','tamil nadu'], statesMed:['maharashtra','uttar pradesh','rajasthan'],
    basePrice:2100, demand:0.85, oversupplyStates:[], inputCost:25000, revenue:55000, riskPests:['fall armyworm'] },
  { id:'redgram', name:'Red Gram (Tur/Arhar)', te:'కందులు', hi:'अरहर (तुअर)', soils:['red','black','red_loam','loam'], seasons:['kharif'], water:'low',
    statesHigh:['maharashtra','karnataka','telangana','madhya pradesh','andhra pradesh'], statesMed:['uttar pradesh','gujarat','jharkhand'],
    basePrice:7550, demand:0.95, oversupplyStates:[], inputCost:22000, revenue:65000, riskPests:['pod borer'] },
  { id:'greengram', name:'Green Gram (Moong)', te:'పెసరలు', hi:'मूंग', soils:['loam','red','red_loam','sandy_loam'], seasons:['kharif','summer'], water:'low',
    statesHigh:['rajasthan','maharashtra','karnataka','andhra pradesh','telangana','tamil nadu'], statesMed:['madhya pradesh','odisha'],
    basePrice:8600, demand:0.9, oversupplyStates:[], inputCost:15000, revenue:42000, riskPests:['yellow mosaic virus'] },
  { id:'groundnut', name:'Groundnut (Peanut)', te:'వేరుశెనగక్కలు', hi:'मूंगफली', soils:['sandy_loam','red','red_loam','loam'], seasons:['kharif','rabi'], water:'medium',
    statesHigh:['gujarat','andhra pradesh','tamil nadu','karnataka','rajasthan'], statesMed:['telangana','maharashtra'],
    basePrice:6800, demand:0.8, oversupplyStates:['gujarat'], inputCost:32000, revenue:72000, riskPests:['leaf spot','aflatoxin'] },
  { id:'chilli', name:'Chilli', te:'మిరపకాయలు', hi:'मिर्च', soils:['red_loam','black','loam'], seasons:['kharif','rabi'], water:'medium',
    statesHigh:['andhra pradesh','telangana','karnataka','madhya pradesh'], statesMed:['tamil nadu','maharashtra','west bengal'],
    basePrice:18500, demand:0.7, oversupplyStates:['andhra pradesh'], inputCost:70000, revenue:180000, riskPests:['thrips','fruit rot'] },
  { id:'turmeric', name:'Turmeric', te:'పసుపు', hi:'हल्दी', soils:['loam','red_loam','clay_loam'], seasons:['kharif'], water:'medium',
    statesHigh:['telangana','tamil nadu','maharashtra','andhra pradesh','karnataka','odisha'], statesMed:['west bengal'],
    basePrice:12800, demand:0.8, oversupplyStates:[], inputCost:60000, revenue:145000, riskPests:['leaf blotch','rhizome rot'] },
  { id:'soybean', name:'Soybean', te:'సోయాబీన్', hi:'सोयाबीन', soils:['black','loam'], seasons:['kharif'], water:'medium',
    statesHigh:['madhya pradesh','maharashtra','rajasthan'], statesMed:['karnataka','telangana','andhra pradesh'],
    basePrice:4600, demand:0.75, oversupplyStates:['madhya pradesh'], inputCost:20000, revenue:48000, riskPests:['girdle beetle'] },
  { id:'wheat', name:'Wheat', te:'గోధుమలు', hi:'गेहूं', soils:['loam','alluvial','black'], seasons:['rabi'], water:'medium',
    statesHigh:['punjab','haryana','uttar pradesh','madhya pradesh','rajasthan','bihar'], statesMed:['gujarat'],
    basePrice:2275, demand:0.7, oversupplyStates:['punjab','haryana'], inputCost:30000, revenue:62000, riskPests:['rust','aphids'] },
  { id:'chickpea', name:'Chickpea (Chana)', te:'శనగలు', hi:'चना', soils:['loam','black','red_loam'], seasons:['rabi'], water:'low',
    statesHigh:['madhya pradesh','rajasthan','maharashtra','karnataka','andhra pradesh','telangana'], statesMed:['uttar pradesh','gujarat'],
    basePrice:5440, demand:0.9, oversupplyStates:[], inputCost:18000, revenue:48000, riskPests:['pod borer','wilt'] },
  { id:'ragi', name:'Ragi (Finger Millet)', te:'రాగి', hi:'रागी', soils:['red','red_loam','sandy_loam','loam'], seasons:['kharif'], water:'low',
    statesHigh:['karnataka','tamil nadu','andhra pradesh','telangana','odisha'], statesMed:['maharashtra','uttarakhand'],
    basePrice:3846, demand:0.85, oversupplyStates:[], inputCost:12000, revenue:35000, riskPests:['blast'] },
  { id:'jowar', name:'Jowar (Sorghum)', te:'జొన్న', hi:'जोवार', soils:['black','red','loam','red_loam'], seasons:['kharif','rabi'], water:'low',
    statesHigh:['maharashtra','karnataka','telangana','andhra pradesh','madhya pradesh'], statesMed:['tamil nadu','rajasthan'],
    basePrice:3225, demand:0.8, oversupplyStates:[], inputCost:14000, revenue:36000, riskPests:['shoot fly','stem borer'] },
  { id:'bajra', name:'Bajra (Pearl Millet)', te:'సజ్జలు', hi:'बाजरा', soils:['sandy','sandy_loam','red'], seasons:['kharif'], water:'low',
    statesHigh:['rajasthan','maharashtra','gujarat','haryana','uttar pradesh'], statesMed:['karnataka','andhra pradesh','tamil nadu'],
    basePrice:2625, demand:0.8, oversupplyStates:[], inputCost:12000, revenue:32000, riskPests:['downy mildew'] },
  { id:'tomato', name:'Tomato', te:'టమాట', hi:'टमाटर', soils:['loam','red_loam','sandy_loam'], seasons:['kharif','rabi'], water:'medium',
    statesHigh:['andhra pradesh','karnataka','madhya pradesh','maharashtra','telangana'], statesMed:['tamil nadu','gujarat'],
    basePrice:1800, demand:0.6, oversupplyStates:['karnataka'], inputCost:55000, revenue:130000, riskPests:['leaf curl virus','early blight'] },
  { id:'onion', name:'Onion', te:'ఉల్లిపాయ', hi:'प्याज', soils:['loam','red_loam','black'], seasons:['kharif','rabi'], water:'medium',
    statesHigh:['maharashtra','karnataka','madhya pradesh','gujarat','andhra pradesh'], statesMed:['telangana','rajasthan','bihar'],
    basePrice:2200, demand:0.85, oversupplyStates:['maharashtra'], inputCost:45000, revenue:110000, riskPests:['thrips','purple blotch'] },
  { id:'sugarcane', name:'Sugarcane', te:'చెరకు', hi:'गन्ना', soils:['loam','black','alluvial'], seasons:['annual'], water:'high',
    statesHigh:['uttar pradesh','maharashtra','karnataka','tamil nadu','andhra pradesh'], statesMed:['telangana','bihar','gujarat'],
    basePrice:340, demand:0.75, oversupplyStates:['uttar pradesh','maharashtra'], inputCost:90000, revenue:170000, riskPests:['top borer','red rot'] },
];

export function getSeasonForDate(d = new Date()) {
  const m = d.getMonth() + 1;
  if (m >= 6 && m <= 10) return 'kharif';
  if (m >= 11 || m <= 3) return 'rabi';
  return 'summer';
}

export function normalizeState(s='') { return String(s||'').toLowerCase().trim(); }
