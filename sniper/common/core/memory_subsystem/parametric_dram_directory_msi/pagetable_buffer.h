#ifndef PAGETABLE_BUFFER_H
#define PAGETABLE_BUFFER_H

#include "subsecond_time.h"
#include "fixed_types.h"
#include <algorithm>
#include <array>
#include <list>
#include <unordered_map>
#include <utility>
#include <vector>

namespace ParametricDramDirectoryMSI
{

class PageTableBuffer
{
public:
   enum class Mode
   {
      LEAF_PT = 1,
      PD = 2
   };

   struct LookupResult
   {
      bool hit;
      IntPtr base_address;
      SubsecondTime latency;
   };

   PageTableBuffer(String name, core_id_t core_id, UInt32 size, UInt32 associativity, ComponentLatency access_latency, Mode mode);

   LookupResult lookup(const std::vector<uint64_t> &vpn_indices, bool count);
   void insert(const std::vector<uint64_t> &vpn_indices, IntPtr base_address);

   Mode getMode() const { return m_mode; }
   UInt32 getAssociativity() const { return m_associativity; }

private:
   struct Key
   {
      std::array<uint64_t, 3> parts;
      size_t num_parts;

      bool operator==(const Key &rhs) const
      {
         return num_parts == rhs.num_parts && std::equal(parts.begin(), parts.begin() + num_parts, rhs.parts.begin());
      }
   };

   struct KeyHash
   {
      size_t operator()(const Key &key) const
      {
         size_t seed = 0;
         for (size_t i = 0; i < key.num_parts; ++i)
         {
            seed ^= std::hash<uint64_t>{}(key.parts[i] + 0x9e3779b9 + (seed << 6) + (seed >> 2));
         }
         return seed;
      }
   };

   struct DirectoryEntry
   {
      size_t set_index;
      std::list<std::pair<Key, IntPtr>>::iterator it;
   };

   Key makeKey(const std::vector<uint64_t> &vpn_indices) const;
   size_t getSetIndex(const Key &key) const;

   UInt32 m_size;
   UInt32 m_associativity;
   UInt32 m_num_sets;

   ComponentLatency m_access_latency;
   Mode m_mode;

   UInt64 m_access;
   UInt64 m_hit;
   UInt64 m_miss;

   std::vector<std::list<std::pair<Key, IntPtr>>> m_sets;
   std::unordered_map<Key, DirectoryEntry, KeyHash> m_directory;
};

}

#endif // PAGETABLE_BUFFER_H
