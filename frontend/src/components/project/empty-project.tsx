import { Card, CardContent } from '@/components/ui/card'

const steps = [
  {
    title: 'Say something, or ask',
    body: 'One box for both. A statement becomes proposed facts; a question just gets answered. A message can do both at once, so nothing has to be classified first.',
  },
  {
    title: 'Check our reading, then submit',
    body: "We show what we understood before anything is stored. Keep, edit, or drop each proposal on its own — a misread you discard leaves no trace.",
  },
  {
    title: 'An admin merges it',
    body: 'Each submitted change queues as its own request. Merging is the only way the record is ever written, and one request carries one change.',
  },
  {
    title: 'Read it through your own lens',
    body: 'NL is the natural-language reading, written for you, filtering out what does not concern you. IR is the neutral record, identical for every member. Flip between them to see where a claim came from.',
  },
]

/** A fresh project has nothing to summarize and nothing to list, so both modes
 * would otherwise bottom out in a one-line refusal. Explain the loop instead —
 * this is the first screen a new member sees. */
export function EmptyProject({
  projectName,
  welcome,
  loading,
}: {
  projectName: string
  /** Written for this reader from their own profile. The steps below are the
   * same for everyone; this part is not. */
  welcome?: string
  loading: boolean
}) {
  return (
    <Card className="ring-border/70 min-h-0 flex-1 overflow-hidden py-0 shadow-[0_1px_2px_rgb(0_0_0/0.04),0_12px_32px_-16px_rgb(0_0_0/0.12)]">
      <CardContent className="h-full overflow-y-auto p-6">
        <div className="mx-auto flex max-w-xl flex-col gap-6">
          <div className="flex flex-col gap-2">
            <h2 className="font-heading text-base font-medium">
              Nothing recorded in {projectName} yet
            </h2>
            <p className="text-muted-foreground text-sm leading-6">
              {loading
                ? 'Reading your profile…'
                : welcome ||
                  'This project keeps one neutral record of what is true, and shows it to each member through their own context.'}
            </p>
          </div>

          <ol className="flex flex-col gap-4">
            {steps.map((step, index) => (
              <li key={step.title} className="flex gap-3">
                <span className="bg-brand/10 text-brand ring-brand/20 flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-medium ring-1">
                  {index + 1}
                </span>
                <div className="flex flex-col gap-1">
                  <p className="text-sm font-medium">{step.title}</p>
                  <p className="text-muted-foreground text-sm leading-6">
                    {step.body}
                  </p>
                </div>
              </li>
            ))}
          </ol>

          <p className="text-muted-foreground text-sm">
            Start below by describing what this project is, in a paragraph or
            two. One message can carry a dozen facts — you review them together
            and approve them in one go.
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
