"use client"

import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar"
import { type User } from "@/types"
import { cn } from "@/lib/utils"

interface UserAvatarProps {
  user: User
  size?: "sm" | "md" | "lg"
  className?: string
}

const sizeClasses = {
  sm: "h-8 w-8",
  md: "h-10 w-10",
  lg: "h-16 w-16",
}

export function UserAvatar({ user, size = "md", className }: UserAvatarProps) {
  const getInitials = (name: string) => {
    return name
      .split("")
      .slice(0, 2)
      .map((char) => char.toUpperCase())
      .join("")
  }

  const avatarUrl = user.avatar_url
    ? user.avatar_url.startsWith("http")
      ? user.avatar_url
      : `http://localhost:8000${user.avatar_url}`
    : null

  return (
    <Avatar className={cn(sizeClasses[size], className)}>
      {avatarUrl && (
        <AvatarImage
          src={avatarUrl}
          alt={user.name}
        />
      )}
      <AvatarFallback>
        {getInitials(user.name)}
      </AvatarFallback>
    </Avatar>
  )
}
