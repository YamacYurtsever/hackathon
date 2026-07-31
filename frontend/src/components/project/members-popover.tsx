import { Button } from '@/components/ui/button'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import type { Member } from '@/types/ir'

/** Members are reference material, not part of the conversation — they live
 * behind a header button rather than below the feed. */
export function MembersPopover({
  members,
  currentUserId,
  viewerIsAdmin,
  busy,
  onPromote,
}: {
  members: Member[]
  currentUserId: string
  viewerIsAdmin: boolean
  busy: boolean
  onPromote: (userId: string) => void
}) {
  return (
    <Popover>
      <PopoverTrigger
        render={
          <Button variant="outline">
            {members.length} {members.length === 1 ? 'member' : 'members'}
          </Button>
        }
      />
      <PopoverContent align="end" className="w-72">
        <div className="flex flex-col">
          {members.map((member) => (
            <div
              key={member.id}
              className="flex items-center justify-between gap-3 border-b py-2 last:border-b-0"
            >
              <div className="flex items-center gap-2">
                <span>{member.username}</span>
                {member.id === currentUserId && (
                  <span className="text-muted-foreground text-xs">(you)</span>
                )}
                {member.is_admin && (
                  <span className="bg-secondary text-secondary-foreground rounded px-1.5 py-0.5 text-xs">
                    admin
                  </span>
                )}
              </div>
              {viewerIsAdmin && !member.is_admin && (
                <Button
                  size="xs"
                  variant="outline"
                  disabled={busy}
                  onClick={() => onPromote(member.id)}
                >
                  Make admin
                </Button>
              )}
            </div>
          ))}
        </div>
      </PopoverContent>
    </Popover>
  )
}
