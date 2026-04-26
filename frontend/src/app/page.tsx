'use client';

// Root redirect - in production would check auth and redirect accordingly
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to chat page (main feature)
    router.replace('/chat');
  }, [router]);

  return null;
}