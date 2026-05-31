import { useEffect, useState } from 'react';

import { AUTH_STATE_EVENT, getStoredCurrentUser } from '../services/aiBrain';

function currentUserName(fallback: string) {
  return getStoredCurrentUser()?.display_name ?? fallback;
}

export function CurrentUserTitle({ fallback }: { fallback: string }) {
  const [name, setName] = useState(() => currentUserName(fallback));

  useEffect(() => {
    const syncName = () => setName(currentUserName(fallback));

    syncName();
    window.addEventListener(AUTH_STATE_EVENT, syncName);
    window.addEventListener('storage', syncName);
    return () => {
      window.removeEventListener(AUTH_STATE_EVENT, syncName);
      window.removeEventListener('storage', syncName);
    };
  }, [fallback]);

  return <span>{name}</span>;
}
