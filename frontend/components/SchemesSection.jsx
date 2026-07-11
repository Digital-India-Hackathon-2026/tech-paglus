'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Landmark } from 'lucide-react';

const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'income', label: 'Income Support' },
  { key: 'loan', label: 'Loans' },
  { key: 'insure', label: 'Insurance' },
  { key: 'state', label: 'Telangana State' },
];

const BADGE_STYLES = {
  central: 'bg-emerald-600 hover:bg-emerald-600',
  loan: 'bg-amber-600 hover:bg-amber-600',
  insure: 'bg-sky-600 hover:bg-sky-600',
  state: 'bg-yellow-500 text-emerald-950 hover:bg-yellow-500',
};

const SCHEMES = [
  {
    cats: ['income'],
    badge: 'central',
    badgeLabel: 'Central Scheme',
    title: 'PM-KISAN Samman Nidhi',
    benefit: '₹6,000 / year — paid in 3 instalments of ₹2,000 directly to your bank account',
    desc: 'A central government scheme for landholding farmer families. Money is transferred straight to your Aadhaar-linked bank account — no middlemen. You\u2019ll need your land records, Aadhaar, and bank details linked and e-KYC completed to keep receiving instalments.',
    who: 'Landholding farmer families',
    metaLabel: 'Helpline',
    metaValue: '155261 / 011-24300606',
    links: [{ label: 'Apply / Check Status →', href: 'https://pmkisan.gov.in/' }, { label: 'Full details', href: 'https://www.myscheme.gov.in/schemes/pm-kisan', secondary: true }],
  },
  {
    cats: ['income', 'state'],
    badge: 'state',
    badgeLabel: 'Telangana State',
    title: 'Rythu Bharosa (Telangana)',
    benefit: '₹12,000 / acre / year — paid as ₹6,000 per season (Kharif + Rabi)',
    desc: 'Telangana\u2019s own farmer investment support scheme, replacing the earlier Rythu Bandhu. Money goes directly to your bank account to cover seeds, fertilizer, and cultivation costs. Your land must be verified on the Bhu Bharati portal (which replaced Dharani). Landless farm workers are covered separately under Indiramma Atmiya Bharosa.',
    who: 'Telangana pattadar farmers, registered tenant farmers',
    metaLabel: 'Apply offline at',
    metaValue: 'Gram Sabha / Gram Panchayat / Praja Palana Centres',
    links: [{ label: 'Check Status →', href: 'https://rythubharosa.telangana.gov.in/' }],
  },
  {
    cats: ['loan'],
    badge: 'loan',
    badgeLabel: 'Bank Loan',
    title: 'Kisan Credit Card (KCC)',
    benefit: 'Up to ₹3 lakh at ~4% effective interest (with on-time repayment)',
    desc: 'A revolving credit line for farmers — draw money as needed for seeds, fertilizer, or post-harvest costs, and repay on your harvest cycle instead of fixed monthly EMIs. Base rate is around 7%, but the government\u2019s interest subvention brings it down to about 4% for farmers who repay on time. Loans up to ₹2 lakh usually need no collateral. Works through any public/private bank, RRB, or cooperative bank — even tenant farmers without land ownership can apply through self-declaration.',
    who: 'Farmers, tenant farmers, sharecroppers, allied workers (dairy, fishery)',
    metaLabel: 'Where to apply',
    metaValue: 'Any bank branch, or online via Jan Samarth Portal',
    links: [{ label: 'Apply Online →', href: 'https://www.jansamarth.in/' }, { label: 'Kisan Rin Portal (track loan)', href: 'https://fasalrin.gov.in/', secondary: true }],
  },
  {
    cats: ['insure'],
    badge: 'insure',
    badgeLabel: 'Crop Insurance',
    title: 'Pradhan Mantri Fasal Bima Yojana (PMFBY)',
    benefit: 'Farmer pays only 1.5–2% premium — rest is subsidized',
    desc: 'Central crop insurance covering losses from drought, flood, pests, storms, and other natural risks — from sowing to post-harvest. Note: Telangana opted out of PMFBY, so if you\u2019re farming in Telangana, check with your local agriculture office or bank about the state\u2019s current crop insurance arrangement before assuming this applies to you.',
    who: 'Landowning and tenant farmers, on notified crops',
    metaLabel: 'Helpline',
    metaValue: '14447 / 1800-180-1551',
    links: [{ label: 'Check Eligibility →', href: 'https://pmfby.gov.in/' }],
  },
  {
    cats: ['insure', 'state'],
    badge: 'state',
    badgeLabel: 'Telangana State',
    title: 'Rythu Bima (Telangana)',
    benefit: '₹5 lakh life cover — premium fully paid by the state',
    desc: 'A group life insurance scheme for registered Telangana farmers aged 18–59. If the farmer passes away for any reason, ₹5 lakh is paid to their nominee within about 10 days — no premium contribution needed from the farmer\u2019s side.',
    who: 'Registered Telangana farmers, age 18–59',
    metaLabel: 'Where to enroll',
    metaValue: 'Local agriculture office, linked to Rythu Bharosa registration',
    links: [{ label: 'More Info →', href: 'https://rythubharosa.telangana.gov.in/' }],
  },
];

export default function SchemesSection() {
  const [filter, setFilter] = useState('all');
  const visible = filter === 'all' ? SCHEMES : SCHEMES.filter((s) => s.cats.includes(filter));

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <Landmark className="h-4 w-4 text-indigo-600" /> Schemes & Loans — money that&apos;s already yours to claim
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-2 mb-4">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={`text-xs font-medium px-3 py-1.5 rounded-full border transition-colors ${
                filter === f.key ? 'bg-indigo-900 text-white border-indigo-900' : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-50'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div className="space-y-3">
          {visible.map((s) => (
            <div key={s.title} className="rounded-lg border p-4">
              <div className="flex items-start justify-between gap-2 flex-wrap mb-1.5">
                <div className="font-semibold text-indigo-900">{s.title}</div>
                <Badge className={`${BADGE_STYLES[s.badge]} text-white`}>{s.badgeLabel}</Badge>
              </div>
              <div className="text-xs font-bold text-emerald-700 mb-1.5">{s.benefit}</div>
              <p className="text-xs text-slate-600 mb-3 leading-relaxed">{s.desc}</p>
              <div className="flex flex-wrap gap-x-6 gap-y-2 text-xs border-t border-dashed pt-2 mb-3">
                <div>
                  <div className="uppercase text-[10px] tracking-wide text-slate-400 font-semibold">Who can apply</div>
                  <div className="text-slate-700">{s.who}</div>
                </div>
                <div>
                  <div className="uppercase text-[10px] tracking-wide text-slate-400 font-semibold">{s.metaLabel}</div>
                  <div className="text-slate-700">{s.metaValue}</div>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {s.links.map((l) => (
                  <a
                    key={l.href}
                    href={l.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`text-xs font-medium px-3 py-1.5 rounded ${
                      l.secondary ? 'border border-slate-300 text-slate-700 hover:bg-slate-50' : 'bg-indigo-900 text-white hover:bg-indigo-800'
                    }`}
                  >
                    {l.label}
                  </a>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-4 rounded-lg border border-dashed border-amber-300 bg-amber-50 p-3 text-xs text-slate-600 leading-relaxed">
          <b className="text-amber-800">Note:</b> Scheme amounts, eligibility, and portals change over time and can vary by state, bank, and season. This is a starting point — always confirm current details, deadlines, and required documents on the official site or with your local agriculture office before applying.
        </div>
      </CardContent>
    </Card>
  );
}
