import './globals.css'
import { Providers } from './providers'

export const metadata = {
  title: 'AgriSarthi AI — Smart Farmer Assistant',
  description: 'Voice-enabled AI agent for Indian farmers. Crop recommendations, weather, mandi, irrigation — personalized by location, soil and season.',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E🌾%3C/text%3E%3C/svg%3E" />
        <script dangerouslySetInnerHTML={{__html:'window.addEventListener("error",function(e){if(e.error instanceof DOMException&&e.error.name==="DataCloneError"&&e.message&&e.message.includes("PerformanceServerTiming")){e.stopImmediatePropagation();e.preventDefault()}},true);'}} />
      </head>
      <body className="antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
