import {NextResponse, type NextRequest} from 'next/server';
import {allowedHost} from './lib/proxy';

export function proxy(request: NextRequest) {
  if (!allowedHost(request.headers.get('host'))) {
    return NextResponse.json({error: 'HOST_REJECTED'}, {status: 400});
  }
  return NextResponse.next();
}

export const config = {matcher: '/:path*'};
