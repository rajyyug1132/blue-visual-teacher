import Link from 'next/link'
import { Wordmark } from './wordmark'

const COLUMNS = [
  {
    title: 'Product',
    links: [
      { href: '/#product', label: 'Preview' },
      { href: '/#how-it-works', label: 'How it works' },
      { href: '/#examples', label: 'Example lessons' },
      { href: '/#languages', label: 'Languages' },
    ],
  },
  {
    title: 'Get started',
    links: [
      { href: '/signup', label: 'Sign up' },
      { href: '/login', label: 'Log in' },
      { href: '/create', label: 'Create a lesson' },
      { href: '/dashboard', label: 'Dashboard' },
    ],
  },
]

export function AppFooter() {
  return (
    <footer className="border-t border-ink bg-cream">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-14 md:grid-cols-[1.4fr_1fr_1fr] md:px-6">
        <div className="max-w-sm">
          <Wordmark />
          <p className="mt-5 text-sm leading-relaxed text-muted-foreground">
            Blue Visual Teacher turns lesson topics into visual, narrated lessons, so complex ideas are easier to see,
            hear and remember.
          </p>
        </div>
        {COLUMNS.map((col) => (
          <nav key={col.title} aria-label={col.title}>
            <h2 className="text-xs font-bold uppercase tracking-[0.2em]">{col.title}</h2>
            <ul className="mt-4 flex flex-col gap-2.5">
              {col.links.map((link) => (
                <li key={link.href}>
                  <Link href={link.href} className="text-sm font-medium hover:underline">
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        ))}
      </div>
      <div className="border-t border-ink">
        <div className="mx-auto flex max-w-7xl flex-col gap-2 px-4 py-5 text-xs font-medium md:flex-row md:items-center md:justify-between md:px-6">
          <p className="font-display font-extrabold">© {new Date().getFullYear()} Blue Visual Teacher</p>
          <p className="text-muted-foreground">Hackathon prototype · features in active development</p>
        </div>
      </div>
    </footer>
  )
}
