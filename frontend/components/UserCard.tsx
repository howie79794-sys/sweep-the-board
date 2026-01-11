"use client"

import { UserAvatar } from "@/components/UserAvatar"
import { type User } from "@/types"
import { cn } from "@/lib/utils"

interface UserCardProps {
  user: User
  showAvatar?: boolean
  className?: string
}

export function UserCard({ user, showAvatar = true, className }: UserCardProps) {
  return (
    <div className={cn("flex items-center gap-3", className)}>
      {showAvatar && <UserAvatar user={user} size="md" />}
      <div>
        <div className="font-semibold">{user.name}</div>
        {user.avatar_url && (
          <div className="text-sm text-muted-foreground">
            已设置头像
          </div>
        )}
      </div>
    </div>
  )
}
