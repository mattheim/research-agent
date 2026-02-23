drop extension if exists "pg_net";

drop trigger if exists "update_email_drafts_updated_at" on "public"."email_drafts";

drop trigger if exists "update_pqls_updated_at" on "public"."pqls";

drop policy "Allow all access to activity_log" on "public"."activity_log";

drop policy "Allow all access to email_drafts" on "public"."email_drafts";

drop policy "Allow all access to enrichments" on "public"."enrichments";

drop policy "Allow all access to pqls" on "public"."pqls";

revoke delete on table "public"."activity_log" from "anon";

revoke insert on table "public"."activity_log" from "anon";

revoke references on table "public"."activity_log" from "anon";

revoke select on table "public"."activity_log" from "anon";

revoke trigger on table "public"."activity_log" from "anon";

revoke truncate on table "public"."activity_log" from "anon";

revoke update on table "public"."activity_log" from "anon";

revoke delete on table "public"."activity_log" from "authenticated";

revoke insert on table "public"."activity_log" from "authenticated";

revoke references on table "public"."activity_log" from "authenticated";

revoke select on table "public"."activity_log" from "authenticated";

revoke trigger on table "public"."activity_log" from "authenticated";

revoke truncate on table "public"."activity_log" from "authenticated";

revoke update on table "public"."activity_log" from "authenticated";

revoke delete on table "public"."activity_log" from "service_role";

revoke insert on table "public"."activity_log" from "service_role";

revoke references on table "public"."activity_log" from "service_role";

revoke select on table "public"."activity_log" from "service_role";

revoke trigger on table "public"."activity_log" from "service_role";

revoke truncate on table "public"."activity_log" from "service_role";

revoke update on table "public"."activity_log" from "service_role";

revoke delete on table "public"."email_drafts" from "anon";

revoke insert on table "public"."email_drafts" from "anon";

revoke references on table "public"."email_drafts" from "anon";

revoke select on table "public"."email_drafts" from "anon";

revoke trigger on table "public"."email_drafts" from "anon";

revoke truncate on table "public"."email_drafts" from "anon";

revoke update on table "public"."email_drafts" from "anon";

revoke delete on table "public"."email_drafts" from "authenticated";

revoke insert on table "public"."email_drafts" from "authenticated";

revoke references on table "public"."email_drafts" from "authenticated";

revoke select on table "public"."email_drafts" from "authenticated";

revoke trigger on table "public"."email_drafts" from "authenticated";

revoke truncate on table "public"."email_drafts" from "authenticated";

revoke update on table "public"."email_drafts" from "authenticated";

revoke delete on table "public"."email_drafts" from "service_role";

revoke insert on table "public"."email_drafts" from "service_role";

revoke references on table "public"."email_drafts" from "service_role";

revoke select on table "public"."email_drafts" from "service_role";

revoke trigger on table "public"."email_drafts" from "service_role";

revoke truncate on table "public"."email_drafts" from "service_role";

revoke update on table "public"."email_drafts" from "service_role";

revoke delete on table "public"."enrichments" from "anon";

revoke insert on table "public"."enrichments" from "anon";

revoke references on table "public"."enrichments" from "anon";

revoke select on table "public"."enrichments" from "anon";

revoke trigger on table "public"."enrichments" from "anon";

revoke truncate on table "public"."enrichments" from "anon";

revoke update on table "public"."enrichments" from "anon";

revoke delete on table "public"."enrichments" from "authenticated";

revoke insert on table "public"."enrichments" from "authenticated";

revoke references on table "public"."enrichments" from "authenticated";

revoke select on table "public"."enrichments" from "authenticated";

revoke trigger on table "public"."enrichments" from "authenticated";

revoke truncate on table "public"."enrichments" from "authenticated";

revoke update on table "public"."enrichments" from "authenticated";

revoke delete on table "public"."enrichments" from "service_role";

revoke insert on table "public"."enrichments" from "service_role";

revoke references on table "public"."enrichments" from "service_role";

revoke select on table "public"."enrichments" from "service_role";

revoke trigger on table "public"."enrichments" from "service_role";

revoke truncate on table "public"."enrichments" from "service_role";

revoke update on table "public"."enrichments" from "service_role";

revoke delete on table "public"."pqls" from "anon";

revoke insert on table "public"."pqls" from "anon";

revoke references on table "public"."pqls" from "anon";

revoke select on table "public"."pqls" from "anon";

revoke trigger on table "public"."pqls" from "anon";

revoke truncate on table "public"."pqls" from "anon";

revoke update on table "public"."pqls" from "anon";

revoke delete on table "public"."pqls" from "authenticated";

revoke insert on table "public"."pqls" from "authenticated";

revoke references on table "public"."pqls" from "authenticated";

revoke select on table "public"."pqls" from "authenticated";

revoke trigger on table "public"."pqls" from "authenticated";

revoke truncate on table "public"."pqls" from "authenticated";

revoke update on table "public"."pqls" from "authenticated";

revoke delete on table "public"."pqls" from "service_role";

revoke insert on table "public"."pqls" from "service_role";

revoke references on table "public"."pqls" from "service_role";

revoke select on table "public"."pqls" from "service_role";

revoke trigger on table "public"."pqls" from "service_role";

revoke truncate on table "public"."pqls" from "service_role";

revoke update on table "public"."pqls" from "service_role";

alter table "public"."activity_log" drop constraint "activity_log_pql_id_fkey";

alter table "public"."email_drafts" drop constraint "email_drafts_pql_id_fkey";

alter table "public"."enrichments" drop constraint "enrichments_pql_id_fkey";

alter table "public"."pqls" drop constraint "pqls_status_check";

drop function if exists "public"."update_updated_at_column"();

alter table "public"."activity_log" drop constraint "activity_log_pkey";

alter table "public"."email_drafts" drop constraint "email_drafts_pkey";

alter table "public"."enrichments" drop constraint "enrichments_pkey";

alter table "public"."pqls" drop constraint "pqls_pkey";

drop index if exists "public"."activity_log_pkey";

drop index if exists "public"."email_drafts_pkey";

drop index if exists "public"."enrichments_pkey";

drop index if exists "public"."pqls_pkey";

drop table "public"."activity_log";

drop table "public"."email_drafts";

drop table "public"."enrichments";

drop table "public"."pqls";


