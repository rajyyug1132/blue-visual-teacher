'use client'

import { AppShell } from './app-shell'
import { CreateView } from './create-view'
import { DashboardView } from './dashboard-view'
import { LessonView } from './lesson-view'

type Props =
  | { view: 'dashboard'; next: string }
  | { view: 'create'; next: string; topic?: string; language?: string }
  | { view: 'lesson'; next: string; id: string; topic?: string; language?: string }

/** Client boundary so server pages can pick a view without passing render functions. */
export function AppShellClient(props: Props) {
  return (
    <AppShell next={props.next}>
      {(session) => {
        if (props.view === 'dashboard') return <DashboardView session={session} />
        if (props.view === 'create') return <CreateView topic={props.topic} language={props.language} />
        return <LessonView id={props.id} topic={props.topic} language={props.language} />
      }}
    </AppShell>
  )
}
