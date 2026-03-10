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
    let revoke = "";
    getAuthImageUrl(src)
      .then((url) => {
        revoke = url;
        setBlobUrl(url);
      })
      .catch(() => setBlobUrl(null));

    return () => {
      if (revoke) URL.revokeObjectURL(revoke);
    };
  }, [src]);

  if (!blobUrl) {
    return (
      <div className={`bg-gray-100 animate-pulse rounded ${className}`} />
    );
  }

  return <img src={blobUrl} alt={alt} className={className} />;
}
