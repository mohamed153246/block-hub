-- Block Hub Pro / Supabase schema
create extension if not exists pgcrypto;
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  username text unique,
  display_name text not null default 'Block Hub User',
  avatar_url text,
  role text not null default 'user' check (role in ('user','moderator','admin')),
  created_at timestamptz not null default now()
);
create table if not exists public.posts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  title text not null,
  slug text not null unique,
  description text not null default '',
  type text not null check (type in ('mod','resource')),
  version text not null,
  loader text not null default 'Any',
  file_path text not null,
  cover_url text,
  status text not null default 'pending' check (status in ('pending','published','rejected')),
  downloads bigint not null default 0,
  created_at timestamptz not null default now()
);
alter table public.profiles enable row level security;
alter table public.posts enable row level security;
create or replace function public.handle_new_user() returns trigger language plpgsql security definer set search_path = public as $$
begin insert into public.profiles(id,display_name) values(new.id,coalesce(new.raw_user_meta_data->>'display_name','Block Hub User')); return new; end; $$;
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users for each row execute procedure public.handle_new_user();
create policy "profiles read" on public.profiles for select using (true);
create policy "profiles own update" on public.profiles for update using (auth.uid()=id);
create policy "posts published read" on public.posts for select using (status='published' or auth.uid()=user_id);
create policy "users insert posts" on public.posts for insert with check (auth.uid()=user_id);
create policy "users update own pending" on public.posts for update using (auth.uid()=user_id) with check (auth.uid()=user_id);
create policy "users delete own" on public.posts for delete using (auth.uid()=user_id);
insert into storage.buckets(id,name,public) values('uploads','uploads',true) on conflict(id) do nothing;
create policy "upload own folder" on storage.objects for insert to authenticated with check (bucket_id='uploads' and (storage.foldername(name))[1]=auth.uid()::text);
create policy "read uploads" on storage.objects for select using (bucket_id='uploads');
create policy "delete own uploads" on storage.objects for delete to authenticated using (bucket_id='uploads' and (storage.foldername(name))[1]=auth.uid()::text);
