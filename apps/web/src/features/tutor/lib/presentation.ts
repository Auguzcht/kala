import type { TutorConversation } from "@/features/tutor/schema/tutor.schema";

export function supportsConversationManagement(
  conversation: TutorConversation,
): boolean {
  return Object.prototype.hasOwnProperty.call(conversation, "pinnedAt");
}

export function groupConversations(list: TutorConversation[]) {
  return {
    Pinned: list.filter((conversation) => Boolean(conversation.pinnedAt)),
    Recents: list.filter((conversation) => !conversation.pinnedAt),
  };
}

export function pickGreeting(
  date: Date,
  courseId: string,
  courseTitle?: string,
): string {
  const hour = date.getHours();
  const salutation =
    hour >= 6 && hour < 12
      ? "Good morning"
      : hour >= 12 && hour < 18
        ? "Good afternoon"
        : hour >= 18 && hour < 22
          ? "Good evening"
          : "Up late?";
  const pool = [
    `${salutation}${salutation.endsWith("?") ? "" : "."} What shall we work through?`,
    "What would you like to understand today?",
    courseTitle
      ? `Ready to dig into ${courseTitle}?`
      : "Ready to explore a new idea?",
  ];
  const seed = `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}:${courseId}`;
  const hash = [...seed].reduce(
    (value, character) => (value * 31 + character.charCodeAt(0)) >>> 0,
    0,
  );
  // Each time-of-day pool keeps its own introduction, including course variants.
  const selected = pool[hash % pool.length];
  return hash % pool.length === 0 ? selected : `${salutation} ${selected}`;
}

export function starterSuggestions(skills: { name: string }[]): string[] {
  const names = [
    ...new Set(skills.map((skill) => skill.name.trim()).filter(Boolean)),
  ];
  if (!names.length) return [];
  if (names.length === 1)
    return [
      `Explain ${names[0]}`,
      `Quiz me on ${names[0]}`,
      `Help me practice ${names[0]}`,
    ];
  return names
    .slice(0, 2)
    .flatMap((name) => [`Explain ${name}`, `Quiz me on ${name}`]);
}

export function dockShape(
  dragging: boolean,
  hasAttachments: boolean,
): "rounded-xl" | "rounded-full" {
  return dragging || hasAttachments ? "rounded-xl" : "rounded-full";
}

export function validateTutorFile(file: File): string | null {
  if (!/\.(txt|md|pdf)$/i.test(file.name))
    return "Only .txt, .md, and .pdf files are supported.";
  if (file.size > 5 * 1024 * 1024) return "Files must be 5MB or smaller.";
  return null;
}

/** One promise per mounted chat: sending and dropping share lazy creation. */
export function createConversationResolver() {
  let pending: Promise<string> | undefined;
  return (activeId: string | undefined, create: () => Promise<string>) => {
    if (activeId) return Promise.resolve(activeId);
    if (!pending) {
      pending = create().catch((error: unknown) => {
        pending = undefined;
        throw error;
      });
    }
    return pending;
  };
}
