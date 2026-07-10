'use client';

import Link from 'next/link';
import { ArrowLeft, Sprout } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import TermsContent from '@/components/TermsContent';

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-slate-50 px-4 py-10">
      <div className="mx-auto max-w-2xl">
        <Link href="/register" className="mb-6 inline-flex items-center gap-1 text-sm text-emerald-700 hover:underline">
          <ArrowLeft className="h-4 w-4" /> Back to sign up
        </Link>
        <Card className="border-slate-200 shadow-sm">
          <CardHeader>
            <div className="mb-1 flex items-center gap-2 text-emerald-700">
              <Sprout className="h-5 w-5" />
              <span className="text-sm font-semibold">AgriSarthi AI</span>
            </div>
            <CardTitle className="text-2xl">Terms &amp; Conditions</CardTitle>
          </CardHeader>
          <CardContent>
            <TermsContent />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
