import { useEffect, useState } from "react";
import { getAuthImageUrl } from "../api";

interface AuthImageProps {
  src: string;
  alt?: string;
  className?: string;
}

export default function AuthImage({ src, alt = "", className }: AuthImageProps) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let createdUrl = "";

    setBlobUrl(null);
    getAuthImageUrl(src)
      .then((url) => {
        if (cancelled) {
          // src o'zgarib ulgurgan — yangi blobni darhol bo'shatamiz
          URL.revokeObjectURL(url);
          return;
        }
        createdUrl = url;
        setBlobUrl(url);
      })
      .catch(() => {
        if (!cancelled) setBlobUrl(null);
      });

    return () => {
      cancelled = true;
      if (createdUrl) URL.revokeObjectURL(createdUrl);
    };
  }, [src]);

  if (!blobUrl) {
    return (
      <div className={`bg-gray-100 animate-pulse rounded ${className}`} />
    );
  }

  return <img src={blobUrl} alt={alt} className={className} />;
}
