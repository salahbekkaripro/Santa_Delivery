import type { NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import GitHubProvider from "next-auth/providers/github";
import GoogleProvider from "next-auth/providers/google";

const googleClientId = process.env.GOOGLE_CLIENT_ID;
const googleClientSecret = process.env.GOOGLE_CLIENT_SECRET;
const githubClientId = process.env.GITHUB_CLIENT_ID;
const githubClientSecret = process.env.GITHUB_CLIENT_SECRET;

const providers: NextAuthOptions["providers"] = [];

if (googleClientId && googleClientSecret) {
  providers.push(
    GoogleProvider({
      clientId: googleClientId,
      clientSecret: googleClientSecret,
    }),
  );
}

if (githubClientId && githubClientSecret) {
  providers.push(
    GitHubProvider({
      clientId: githubClientId,
      clientSecret: githubClientSecret,
    }),
  );
}

if (providers.length === 0) {
  providers.push(
    CredentialsProvider({
      name: "Local disabled",
      credentials: {},
      async authorize() {
        return null;
      },
    }),
  );
}

export const authOptions: NextAuthOptions = {
  secret: process.env.NEXTAUTH_SECRET,
  session: {
    strategy: "jwt",
  },
  providers,
  pages: {
    signIn: "/login",
  },
  callbacks: {
    async jwt({ token, account }) {
      if (account?.provider) {
        token.oauth_provider = account.provider;
      }
      if (account?.providerAccountId) {
        token.oauth_account_id = account.providerAccountId;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        (session.user as Record<string, unknown>).id = String(token.sub ?? token.oauth_account_id ?? "");
        (session.user as Record<string, unknown>).oauth_provider = String(token.oauth_provider ?? "");
        (session.user as Record<string, unknown>).oauth_account_id = String(
          token.oauth_account_id ?? token.sub ?? "",
        );
      }
      return session;
    },
  },
};
