import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { themedDialogClass } from '@/lib/themed-dialog'
import type { UiTheme } from '@/lib/ui-theme'
import type { Member } from '@/types/ir'

/** Members are reference material, not part of the conversation — they live
 * behind a header button rather than below the feed, in the same centered
 * dialog the digest and the pending queue use. */
export function MembersPopover({
  members,
  currentUserId,
  viewerIsAdmin,
  busy,
  theme = 'classic',
  onPromote,
}: {
  members: Member[]
  currentUserId: string
  viewerIsAdmin: boolean
  busy: boolean
  theme?: UiTheme
  onPromote: (userId: string) => void
}) {
  return (
    <Dialog>
      <DialogTrigger
        render={
          <Button variant="outline">
            {members.length} {members.length === 1 ? 'member' : 'members'}
          </Button>
        }
      />
      <DialogContent
        className={themedDialogClass(
          theme,
          'max-h-[85svh] overflow-y-auto sm:max-w-lg',
        )}
      >
        <DialogHeader>
          <DialogTitle>
            {members.length} {members.length === 1 ? 'member' : 'members'}
          </DialogTitle>
        </DialogHeader>

        <div className="flex flex-col">
          {members.map((member) => (
            <div
              key={member.id}
              className="flex items-center justify-between gap-3 border-b py-2 last:border-b-0"
            >
              <div className="flex min-w-0 items-center gap-2">
                <span className="truncate">{member.username}</span>
                {member.id === currentUserId && (
                  <span className="text-muted-foreground shrink-0 text-xs">
                    (you)
                  </span>
                )}
              </div>
              {/* Status and action share the right edge, so the column reads
                  down at a glance instead of ragging with each name. */}
              {member.is_admin ? (
                <span className="bg-brand/10 text-brand ring-brand/20 shrink-0 rounded px-1.5 py-0.5 text-xs font-medium ring-1">
                  admin
                </span>
              ) : (
                viewerIsAdmin && (
                  <Button
                    size="xs"
                    variant="outline"
                    disabled={busy}
                    onClick={() => onPromote(member.id)}
                  >
                    Make admin
                  </Button>
                )
              )}
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  )
}
