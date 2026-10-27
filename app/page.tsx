import { Navbar } from '@/components/site/navbar'
import { AppFooter } from '@/components/site/app-footer'
import { HeroSection } from '@/components/landing/hero-section'
import { HowItWorks } from '@/components/landing/how-it-works'
import { ExampleLessons } from '@/components/landing/example-lessons'
import { LanguagesSection } from '@/components/landing/languages-section'
import { BenefitsSection, FinalCta } from '@/components/landing/benefits-section'

export default function HomePage() {
  return (
    <>
      <Navbar />
      <main>
        <HeroSection />
        <HowItWorks />
        <ExampleLessons />
        <LanguagesSection />
        <BenefitsSection />
        <FinalCta />
      </main>
      <AppFooter />
    </>
  )
}
