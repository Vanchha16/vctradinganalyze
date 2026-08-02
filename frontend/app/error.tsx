"use client";

import { useEffect } from "react";

import { Button } from "@/components/ui/button";
import { ErrorPage } from "@/components/shared/error-page";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.error(error);
  }, [error]);

  return (
    <ErrorPage
      title="Something went wrong"
      description="An unexpected error occurred. You can try again, or head back to the dashboard."
      action={
        <Button variant="secondary" onClick={reset}>
          Try again
        </Button>
      }
    />
  );
}
