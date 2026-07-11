import { NextResponse } from 'next/server';

// Keep this list in sync with CATEGORY_OPTIONS in app/community/page.js
const CATEGORY_OPTIONS = [
  'Crop disease/pest',
  'Soil & fertilizer',
  'Water & irrigation',
  'Market / selling',
  'Weather damage',
  'Other',
];

export async function POST(request) {
  try {
    const { base64Data, mimeType } = await request.json();
    if (!base64Data) {
      return NextResponse.json({ error: 'No image data provided' }, { status: 400 });
    }

    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) {
      // No key configured -> fail quietly, client falls back to manual category pick
      return NextResponse.json({ category: null });
    }

    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-6',
        max_tokens: 100,
        messages: [
          {
            role: 'user',
            content: [
              { type: 'image', source: { type: 'base64', media_type: mimeType || 'image/jpeg', data: base64Data } },
              {
                type: 'text',
                text:
                  'This is a photo of a farm problem shared in a farmer community app. Look at the photo and pick exactly one category from this list that best matches what is shown: ' +
                  CATEGORY_OPTIONS.join(', ') +
                  '. Respond with ONLY the category text exactly as written above, nothing else.',
              },
            ],
          },
        ],
      }),
    });

    const data = await response.json();
    const textBlock = (data.content || []).find((b) => b.type === 'text');
    const guess = textBlock ? textBlock.text.trim() : '';
    const match = CATEGORY_OPTIONS.find((opt) => guess.toLowerCase().includes(opt.toLowerCase()));

    return NextResponse.json({ category: match || null });
  } catch (err) {
    console.error('detect-category failed:', err);
    return NextResponse.json({ category: null });
  }
}
